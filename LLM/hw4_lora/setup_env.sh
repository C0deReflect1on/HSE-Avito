#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

python3.11 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
"$VENV_DIR/bin/python" -m pip check
"$VENV_DIR/bin/python" -m ipykernel install --user \
    --name hse-hw4-lora \
    --display-name "Python (hw4_lora)"

printf '\nEnvironment: %s\nJupyter kernel: Python (hw4_lora)\n' "$VENV_DIR"
