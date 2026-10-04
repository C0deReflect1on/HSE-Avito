#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
CONFIGS = [
    "configs/baseline.json",
    "configs/per_device_32.json",
    "configs/accum_128.json",
    "configs/lr_1e3.json",
    "configs/scheduler_linear.json",
]


def run_config(config):
    name = Path(config).stem
    log_path = LOG_DIR / f"{name}.log"
    print(f"START {name}", flush=True)
    print(f"LOG   {log_path}", flush=True)
    command = [
        "docker", "run", "--rm", "--gpus", "all",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--shm-size=16g",
        "-e", "HOME=/app",
        "-e", "HF_HOME=/app/.cache/huggingface",
        "-e", "HF_DATASETS_CACHE=/app/.cache/huggingface/datasets",
        "-e", "PYTHONUNBUFFERED=1",
        "-v", f"{ROOT}:/app",
        "-w", "/app",
        "qwen-trainer",
        "python3", "-u", "run_hw1.py", config,
    ]
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log.write(line)
            log.flush()
        return process.wait()


def main():
    LOG_DIR.mkdir(exist_ok=True)
    results = []
    for config in CONFIGS:
        code = run_config(config)
        results.append((Path(config).stem, code))
        print(f"DONE {results[-1][0]} exit={code}", flush=True)
    print("SUMMARY", flush=True)
    for name, code in results:
        print(f"  {name}: {code}", flush=True)
    return 0 if all(code == 0 for _, code in results) else 1


if __name__ == "__main__":
    sys.exit(main())
