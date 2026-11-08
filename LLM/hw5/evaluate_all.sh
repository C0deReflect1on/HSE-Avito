#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
GPU="${GPU:-1}"
IMAGE="${IMAGE:-rlvr-homework}"

# Run this script in the dev-machine terminal, outside the notebook container.
docker run --rm --gpus "device=$GPU" --ipc=host \
    -v "$SCRIPT_DIR":/workspace -v rlvr-hf-cache:/cache \
    "$IMAGE" python3 evaluate.py Qwen/Qwen3.5-2B --output artifacts/baseline

for run in rl_exact rl_shaped rl_lr; do
    mkdir -p "artifacts/$run"
    for file in config.json summary.json history.json validation_metrics.json; do
        cp "results/$run/$file" "artifacts/$run/$file"
    done
    gzip -c "results/$run/generations.jsonl" > "artifacts/$run/generations.jsonl.gz"
    gzip -c "results/$run/validation_generations.jsonl" > "artifacts/$run/validation_generations.jsonl.gz"

    docker run --rm --gpus "device=$GPU" --ipc=host \
        -v "$SCRIPT_DIR":/workspace -v rlvr-hf-cache:/cache \
        "$IMAGE" python3 evaluate.py "checkpoints/$run/final" --output "artifacts/$run"
done

cp data/experiments/preparation.json artifacts/preparation.json
printf '\nГотово: artifacts/ содержит результаты для Git и анализа без GPU.\n'
