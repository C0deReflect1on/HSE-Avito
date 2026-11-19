#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

nvidia-smi -i 0 -L
sudo -n docker build -t hw6-safin:v0 .

python3 -m venv .hw6_driver
.hw6_driver/bin/python -m pip install --upgrade pip
.hw6_driver/bin/python -m pip install 'matplotlib>=3.8,<4' 'nbformat>=5,<6'

printf '\nЗапуск только на GPU 0:\n'
printf '  .hw6_driver/bin/python -u hw6_experiments.py\n'
