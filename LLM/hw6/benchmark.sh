#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

url="${URL:-http://localhost:8000}"
data="data/requests.jsonl"
output="${1:-results/$(date +%Y%m%d-%H%M%S)}"
rpm="${2:-120}"
mkdir -p "$(dirname "$output")"
mkdir "$output"

# Очищаем кеш
reset_cache() { curl --noproxy '*' -fsS --max-time 15 -X POST "$url/reset_prefix_cache" >/dev/null; }
reset_cache
trap reset_cache EXIT

rps="$(awk -v rpm="$rpm" 'BEGIN { printf "%.12g", rpm / 60 }')"

aiperf profile --url "$url" --model Qwen/Qwen3-8B \
  --endpoint-type chat --custom-dataset-type raw_payload \
  --input-file "$data" --dataset-sampling-strategy sequential \
  --warmup-request-count 40 --warmup-concurrency 8 \
  --request-count "$(wc -l < "$data")" \
  --request-rate "$rps" --arrival-pattern constant --random-seed 42 \
  --streaming --request-timeout-seconds 120 \
  --export-level records --export-outputs-json --output-artifact-dir "$output/profile"
