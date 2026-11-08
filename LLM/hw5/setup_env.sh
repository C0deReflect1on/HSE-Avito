#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Этот скрипт предназначен для Linux dev-машины с NVIDIA GPU." >&2
    exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Нужен Python 3.11+. Запусти: PYTHON_BIN=python3.12 bash setup_env.sh")
PY

nvidia-smi
"$PYTHON_BIN" -m venv .venv
PYTHON="$SCRIPT_DIR/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install "torch==2.11.0" \
    --index-url https://download.pytorch.org/whl/cu129
"$PYTHON" -m pip install \
    "torch==2.11.0" "numpy==2.2.6" \
    "trl==1.16.0" "transformers==5.9.0" "peft==0.18.1" \
    "datasets==4.7.0" "accelerate==1.10.1" \
    "flash-linear-attention==0.4.1" "ipykernel>=6,<8"
"$PYTHON" -m pip install \
    "https://github.com/vllm-project/vllm/releases/download/v0.22.0/vllm-0.22.0%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
    --extra-index-url https://download.pytorch.org/whl/cu129
"$PYTHON" -m pip check

"$PYTHON" - <<'PY'
import torch
if not torch.cuda.is_available():
    raise SystemExit("PyTorch не видит CUDA. Проверь доступ к GPU и совместимость драйвера с CUDA 12.9.")
if not torch.cuda.is_bf16_supported():
    raise SystemExit("Текущий smoke-конфиг требует GPU с поддержкой bfloat16.")
print("PyTorch:", torch.__version__)
print("CUDA runtime:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name())
PY

"$PYTHON" -m ipykernel install --user \
    --name hse-hw5 --display-name "Python (hw5)"

if [[ ! -f data/raw/data.json ]]; then
    "$PYTHON" download_data.py
fi

printf '\nГотово. Venv: %s/.venv\n' "$SCRIPT_DIR"
printf 'В notebook выбери kernel: Python (hw5)\n'
printf 'Данные: %s/data/raw/data.json\n' "$SCRIPT_DIR"
printf 'Далее выполни gpu_smoke.ipynb. Обучение этим скриптом не запускалось.\n'
