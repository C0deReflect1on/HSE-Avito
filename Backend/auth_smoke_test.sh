#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8003}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

COOKIE_JAR="$TMP_DIR/cookies.txt"

print_step() {
  printf "\n==> %s\n" "$1"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf "[OK] %s\n" "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf "[FAIL] %s\n" "$1"
}

assert_eq() {
  local got="$1"
  local expected="$2"
  local message="$3"
  if [[ "$got" == "$expected" ]]; then
    pass "$message (got: $got)"
  else
    fail "$message (got: $got, expected: $expected)"
  fi
}

http_call() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local cookie_file="${4:-}"
  local extra_header="${5:-}"

  local headers_file="$TMP_DIR/headers.txt"
  local body_file="$TMP_DIR/body.txt"
  local args=(
    -sS
    -X "$method"
    -D "$headers_file"
    -o "$body_file"
    -H "Content-Type: application/json"
  )

  if [[ -n "$cookie_file" ]]; then
    args+=(-b "$cookie_file" -c "$cookie_file")
  fi

  if [[ -n "$extra_header" ]]; then
    args+=(-H "$extra_header")
  fi

  if [[ -n "$body" ]]; then
    args+=(-d "$body")
  fi

  local status
  status="$(curl "${args[@]}" "${BASE_URL}${path}" -w "%{http_code}")"

  HTTP_STATUS="$status"
  HTTP_HEADERS="$(<"$headers_file")"
  HTTP_BODY="$(<"$body_file")"
}

seed_accounts() {
  print_step "Seeding test accounts in PostgreSQL"
  docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d hw <<'SQL'
INSERT INTO account (login, password, is_blocked)
VALUES
  ('active_user', md5('active_pass'), FALSE),
  ('blocked_user', md5('blocked_pass'), TRUE)
ON CONFLICT (login)
DO UPDATE SET
  password = EXCLUDED.password,
  is_blocked = EXCLUDED.is_blocked;
SQL
  pass "Accounts seeded (active_user, blocked_user)"
}

print_step "Auth smoke tests: $BASE_URL"

seed_accounts

print_step "1) POST /login success"
http_call "POST" "/login" '{"login":"active_user","password":"active_pass"}' "$COOKIE_JAR"
assert_eq "$HTTP_STATUS" "200" "Login with valid credentials"
if [[ "$HTTP_HEADERS" == *"set-cookie:"* && "$HTTP_HEADERS" == *"access_token="* && "$HTTP_HEADERS" == *"HttpOnly"* ]]; then
  pass "Response includes HttpOnly access_token cookie"
else
  fail "Response does not include HttpOnly access_token cookie"
fi

print_step "2) POST /login invalid credentials"
http_call "POST" "/login" '{"login":"active_user","password":"wrong"}'
assert_eq "$HTTP_STATUS" "401" "Login with invalid password"

print_step "3) POST /login blocked account"
http_call "POST" "/login" '{"login":"blocked_user","password":"blocked_pass"}'
assert_eq "$HTTP_STATUS" "403" "Login with blocked account"

print_step "4) Protected endpoint without cookie"
http_call "GET" "/moderation_result/999999"
assert_eq "$HTTP_STATUS" "401" "Protected endpoint rejects anonymous user"

print_step "5) Protected endpoint with malformed token"
http_call "GET" "/moderation_result/999999" "" "" "Cookie: access_token=not-a-jwt"
assert_eq "$HTTP_STATUS" "401" "Protected endpoint rejects invalid token"

print_step "6) Protected endpoint with valid cookie"
http_call "GET" "/moderation_result/999999" "" "$COOKIE_JAR"
if [[ "$HTTP_STATUS" == "404" || "$HTTP_STATUS" == "200" ]]; then
  pass "Authorized request passes auth check (status: $HTTP_STATUS)"
else
  fail "Authorized request did not pass auth check (status: $HTTP_STATUS, expected 404 or 200)"
fi

print_step "Summary"
printf "Passed: %d\n" "$PASS_COUNT"
printf "Failed: %d\n" "$FAIL_COUNT"

if (( FAIL_COUNT > 0 )); then
  exit 1
fi
