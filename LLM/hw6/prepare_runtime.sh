#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

image="$(awk '$1 == "FROM" { print $2; exit }' Dockerfile)"
if ! docker image inspect "$image" >/dev/null 2>&1; then
    docker pull "$image"
fi

docker run --rm \
    --mount type=volume,source=hw6-safin-huggingface,target=/root/.cache/huggingface \
    --env HF_HOME=/root/.cache/huggingface \
    --entrypoint python3 "$image" -c '
from huggingface_hub import snapshot_download

snapshot_download("Qwen/Qwen3-8B")
'

printf '\nОбраз и веса готовы. В run_hw6.ipynb выберите своё ядро и нажмите Run All.\n'