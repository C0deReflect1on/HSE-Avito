#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${BASE_DIR}/migrations.yml"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config not found: $CONFIG_FILE" >&2
  exit 1
fi

CONN_LINE="$(grep -E '^conn:' "$CONFIG_FILE" | head -n 1 || true)"
if [[ -z "$CONN_LINE" ]]; then
  echo "conn not found in $CONFIG_FILE" >&2
  exit 1
fi

CONN="${CONN_LINE#conn: }"
CONN="${CONN%\"}"
CONN="${CONN#\"}"

TARGET="${1:-latest}"

pgmigrate -d "$BASE_DIR" -c "$CONN" migrate -t "$TARGET"
