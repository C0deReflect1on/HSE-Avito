"""Create two PNG figures from completed HW2 experiments."""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "results" / "experiment_index.json"


def read_summary(path: str) -> dict:
    values = json.loads((ROOT / path / "summary.json").read_text())
    for key in ("tokens_per_second", "peak_allocated_gib", "validation_loss"):
        if values[key] is None or not math.isfinite(values[key]):
            raise ValueError(f"Некорректное значение {key} в {path}")
    return values


def plot() -> None:
    index = json.loads(INDEX.read_text())
    screen = index["screen"]
    finals = index["finals"]
    if len(screen) != 6 or len(finals) != 2:
        raise ValueError("Нужны шесть конфигураций и два полных повторных запуска")

    names = list(screen)
    screening = [read_summary(screen[name]) for name in names]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), layout="constrained")
    axes[0].bar(names, [row["tokens_per_second"] for row in screening], color="#2676a8")
    axes[0].set(title="Полезные токены/с", ylabel="токены/с")
    axes[1].bar(names, [row["peak_allocated_gib"] for row in screening], color="#bd6b39")
    axes[1].set(title="Пик выделенной памяти GPU", ylabel="ГиБ")
    fig.suptitle("B0: 300 с; B1–B5: 90 с")
    fig.savefig(ROOT / "throughput_memory.png", dpi=180)
    plt.close(fig)

    full = {"B0": screen["B0"], **finals}
    names = list(full)
    rows = [read_summary(full[name]) for name in names]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), layout="constrained")
    axes[0].bar(names, [row["tokens_per_second"] for row in rows], color="#2676a8")
    axes[0].set(title="Полезные токены/с", ylabel="токены/с")
    axes[1].bar(names, [row["validation_loss"] for row in rows], color="#5d8d57")
    axes[1].set(title="Лосс валидации", ylabel="NLL")
    fig.suptitle("Полные запуски: по 300 с")
    fig.savefig(ROOT / "full_runs.png", dpi=180)
    plt.close(fig)
    print("Готово: throughput_memory.png, full_runs.png")


if __name__ == "__main__":
    plot()
