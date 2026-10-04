#!/usr/bin/env python3
"""Build the report plots from training logs. Skips smoke and subset runs."""

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
ARTIFACTS = ROOT / "artifacts"
CONFIGS = ROOT / "configs"
RUNS = [
    "baseline",
    "per_device_32",
    "accum_128",
    "lr_1e3",
    "scheduler_linear",
]
SEQ_LENGTH = 512
TOKEN_RE = re.compile(
    r"\|\s*(\d+)/(\d+)\s*\["
    r"|(\{[^{}]*'(?:loss|eval_loss)'[^{}]*\})"
)
STOPPED_RE = re.compile(r"Training stopped after ([0-9.]+) seconds")


def parse_log(name):
    text = (LOG_DIR / f"{name}.log").read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r", "\n")
    config = json.loads((CONFIGS / f"{name}.json").read_text(encoding="utf-8"))
    per_device = config["per_device_train_batch_size"]
    accumulation = config["gradient_accumulation_steps"]
    effective = per_device * accumulation
    step = None
    train = []
    eval_points = []
    for match in TOKEN_RE.finditer(text):
        if match.group(1):
            seen_step = int(match.group(1))
            epoch_steps = int(match.group(2))
            if epoch_steps > 1000:
                step = seen_step
            continue
        if step is None:
            continue
        entry = ast.literal_eval(match.group(3))
        if "eval_loss" in entry:
            eval_points.append((step, float(entry["eval_loss"])))
        elif "loss" in entry:
            train.append((step, float(entry["loss"])))
    stopped = STOPPED_RE.search(text)
    metrics_path = ARTIFACTS / name / "metrics.json"
    trace_path = ARTIFACTS / name / "trace.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {}
    trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.is_file() else {}
    disk_full = "No space left on device" in text
    last_step = train[-1][0] if train else None
    return {
        "name": name,
        "finished": metrics_path.is_file() and not disk_full,
        "disk_full": disk_full,
        "per_device": per_device,
        "accumulation": accumulation,
        "effective": effective,
        "learning_rate": config["learning_rate"],
        "scheduler": config["lr_scheduler_type"],
        "train": train,
        "eval": eval_points,
        "last_step": last_step,
        "last_train_loss": train[-1][1] if train else None,
        "best_eval": min((point[1] for point in eval_points), default=None),
        "final_eval": metrics.get("eval_loss"),
        "perplexity": metrics.get("perplexity"),
        "stopped_after": float(stopped.group(1)) if stopped else None,
        "tokens_seen": trace.get("tokens_seen", (last_step or 0) * effective * SEQ_LENGTH),
        "train_seconds": trace.get("train_seconds"),
        "eval_seconds": trace.get("eval_seconds"),
        "eval_fraction": trace.get("eval_fraction"),
        "optimizer_steps": trace.get("optimizer_steps", last_step),
    }


def project(x, y, bounds, frame):
    min_x, max_x, min_y, max_y = bounds
    left, right, top, bottom, width, height = frame
    px = left + (x - min_x) / (max_x - min_x) * (width - left - right)
    py = height - bottom - (y - min_y) / (max_y - min_y) * (height - top - bottom)
    return px, py


def write_svg(path, title, ylabel, xlabel, series, x_of):
    width, height = 960, 560
    left, right, top, bottom = 70, 300, 50, 50
    frame = (left, right, top, bottom, width, height)
    points = []
    for item in series:
        points.extend((x_of(item, x, y), y) for x, y in item["points"])
        if item.get("marker") is not None and item.get("marker_x") is not None:
            points.append((item["marker_x"], item["marker"]))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if max_x == min_x:
        max_x += 1
    if max_y == min_y:
        max_y += 1
    pad_y = (max_y - min_y) * 0.05
    bounds = (min_x, max_x, min_y - pad_y, max_y + pad_y)
    colors = ["#7f7f7f", "#ff7f0e", "#1f77b4", "#2ca02c", "#d62728"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16">{title}</text>',
        f'<text x="24" y="{height / 2}" transform="rotate(-90 24 {height / 2})" '
        f'text-anchor="middle" font-size="14">{ylabel}</text>',
        f'<text x="{(left + width - right) / 2}" y="{height - 12}" text-anchor="middle" '
        f'font-size="14">{xlabel}</text>',
    ]
    for index, item in enumerate(series):
        color = colors[index % len(colors)]
        coords = " ".join(
            f"{project(x_of(item, x, y), y, bounds, frame)[0]:.1f},"
            f"{project(x_of(item, x, y), y, bounds, frame)[1]:.1f}"
            for x, y in item["points"]
        )
        dash = ' stroke-dasharray="6 4"' if item.get("dashed") else ""
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2"{dash} points="{coords}"/>'
        )
        for x, y in item.get("marks", []):
            px, py = project(x_of(item, x, y), y, bounds, frame)
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{color}"/>')
        if item.get("marker") is not None and item.get("marker_x") is not None:
            px, py = project(item["marker_x"], item["marker"], bounds, frame)
            parts.append(
                f'<rect x="{px - 4:.1f}" y="{py - 4:.1f}" width="8" height="8" fill="{color}"/>'
            )
        legend_y = top + index * 22
        parts.append(
            f'<line x1="{width - right + 16}" y1="{legend_y}" x2="{width - right + 40}" '
            f'y2="{legend_y}" stroke="{color}" stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="{width - right + 48}" y="{legend_y + 4}" font-size="12">{item["label"]}</text>'
        )
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")


def main():
    runs = [parse_log(name) for name in RUNS]
    ARTIFACTS.mkdir(exist_ok=True)
    train_series = []
    eval_series = []
    for run in runs:
        status = "" if run["finished"] else ", оборван"
        label = (
            f"{run['name']} (batch={run['effective']}, lr={run['learning_rate']}, "
            f"{run['scheduler']}{status})"
        )
        train_series.append({
            "label": label,
            "points": run["train"],
            "marks": run["eval"],
            "marker": run["final_eval"],
            "marker_x": run["last_step"] if run["final_eval"] is not None else None,
            "dashed": not run["finished"],
            "effective": run["effective"],
        })
        if run["eval"]:
            eval_series.append({
                "label": label,
                "points": run["eval"],
                "marks": run["eval"],
                "dashed": not run["finished"],
                "effective": run["effective"],
            })
    write_svg(
        ARTIFACTS / "comparison.svg",
        "Сравнение сходимости претрейна Qwen3-1B за 15 минут (A100)",
        "Loss",
        "Шаги оптимизации",
        train_series,
        lambda item, x, y: x,
    )
    write_svg(
        ARTIFACTS / "comparison_tokens.svg",
        "Сравнение по числу увиденных токенов, Qwen3-1B, 15 минут (A100)",
        "Loss",
        "Токены",
        train_series,
        lambda item, x, y: x * item["effective"] * SEQ_LENGTH,
    )
    write_svg(
        ARTIFACTS / "eval_comparison.svg",
        "Eval loss на отложенных 5000 статьях, Qwen3-1B (A100)",
        "Eval loss",
        "Шаги оптимизации",
        eval_series,
        lambda item, x, y: x,
    )
    for run in runs:
        print(
            f"{run['name']}: steps={run['optimizer_steps']} "
            f"train_loss={run['last_train_loss']} eval={run['final_eval'] or run['best_eval']} "
            f"tokens={run['tokens_seen']} finished={run['finished']}"
        )


if __name__ == "__main__":
    main()
