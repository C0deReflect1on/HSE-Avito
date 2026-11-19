#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python_bin="${PYTHON_BIN:-python3}"
"$python_bin" - <<'PY'
import sys

if not (3, 11) <= sys.version_info[:2] < (3, 14):
    raise SystemExit("Нужен Python 3.11–3.13. Пример: PYTHON_BIN=python3.12 bash setup_env.sh")
if sys.platform != "linux":
    raise SystemExit("Запустите setup_env.sh на Linux-сервере с NVIDIA GPU.")
PY

command -v curl >/dev/null
nvidia-smi -L
docker info --format '{{.ServerVersion}}'

"$python_bin" -m venv .hw6_safin_venv
venv_python="$PWD/.hw6_safin_venv/bin/python"
"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install \
    'aiperf==0.13.0' 'transformers==5.22.1' \
    'ipykernel>=6,<8' 'jupyterlab>=4,<5' 'nbformat>=5,<6' 'matplotlib>=3.8,<4'
"$venv_python" -m pip check
"$venv_python" -m ipykernel install --user \
    --name hw6_safin --display-name 'Python (hw6_safin)'

image="$(awk '$1 == "FROM" { print $2; exit }' Dockerfile)"
docker pull "$image"

printf '\nОткройте run_hw6.ipynb и выберите Python (hw6_safin).\n'
printf 'Если Jupyter ещё не запущен: .hw6_safin_venv/bin/jupyter lab\n'
