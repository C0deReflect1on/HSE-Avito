#!/usr/bin/env python3
"""Build PNG report plots from saved training histories. Skips smoke and subset runs."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
RUNS = ["baseline", "per_device_32", "accum_128", "lr_1e3", "scheduler_linear"]
SEQ_LENGTH = 512
COLORS = ["#68717a", "#d97816", "#2176ae", "#24834b", "#bc3341"]


def write_png(path, title, ylabel, xlabel, series, x_of=lambda item, x, y: x):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    has_eval = has_final = False
    for index, item in enumerate(series):
        color = item.get("color", COLORS[index % len(COLORS)])
        points = item["points"]
        if points:
            ax.plot(
                [x_of(item, x, y) for x, y in points],
                [y for _, y in points],
                color=color, label=item["label"], linewidth=1.3,
                linestyle="--" if item.get("dashed") else "-",
            )
        marks = item.get("marks", [])
        if marks:
            ax.scatter(
                [x_of(item, x, y) for x, y in marks], [y for _, y in marks],
                color=color, s=28, zorder=3,
            )
            has_eval = True
        if item.get("marker") is not None and item.get("marker_x") is not None:
            ax.scatter(
                x_of(item, item["marker_x"], item["marker"]), item["marker"],
                color=color, marker="s", s=55, edgecolors="white", zorder=4,
            )
            has_final = True
    ax.set(title=title, ylabel=ylabel, xlabel=xlabel)
    ax.set_xlim(left=0)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8, integer=True))
    if xlabel == "Обработанные позиции токенов, млн":
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1e6:g}"))
    ax.grid(alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    if has_eval:
        handles.append(Line2D([], [], color="#444444", marker="o", linestyle="none"))
        labels.append("Промежуточная валидация")
    if has_final:
        handles.append(Line2D([], [], color="#444444", marker="s", linestyle="none"))
        labels.append("Оценка выбранного checkpoint")
    if handles:
        ax.legend(handles, labels, loc="upper right", fontsize=9, framealpha=0.95)
    fig.savefig(path, dpi=180, facecolor="white", format="png")
    plt.close(fig)


def main():
    train_series, eval_series = [], []
    for index, name in enumerate(RUNS):
        folder = ARTIFACTS / name
        history = json.loads((folder / "loss.json").read_text(encoding="utf-8"))
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
        trace = json.loads((folder / "trace.json").read_text(encoding="utf-8"))
        state = json.loads((ROOT / "output_dir" / name / "trainer_state.json").read_text(encoding="utf-8"))
        # The explicit final evaluation follows train_runtime and can use an earlier checkpoint.
        training_history = history[:next(i for i, entry in enumerate(history) if "train_runtime" in entry)]
        train = [(entry["step"], entry["loss"]) for entry in training_history if "loss" in entry]
        evaluations = [(entry["step"], entry["eval_loss"]) for entry in training_history if "eval_loss" in entry]
        best_step = int(Path(state["best_model_checkpoint"]).name.rsplit("-", 1)[1])
        item = {
            "label": f"{name} (batch={trace['effective_batch_size']})",
            "points": train,
            "marks": evaluations,
            "marker": metrics["eval_loss"],
            "marker_x": best_step,
            "effective": trace["effective_batch_size"],
            "color": COLORS[index],
        }
        train_series.append(item)
        eval_series.append({**item, "points": evaluations})
        write_png(
            folder / "loss.png", f"{name}: обучение и валидация", "Loss",
            "Шаги оптимизатора", [item],
        )
        print(f"{name}: steps={trace['optimizer_steps']}, best_step={best_step}, eval_loss={metrics['eval_loss']:.6f}")
    write_png(
        ARTIFACTS / "comparison.png", "Qwen3-1B: loss по шагам оптимизатора", "Loss",
        "Шаги оптимизатора", train_series,
    )
    write_png(
        ARTIFACTS / "comparison_tokens.png", "Qwen3-1B: loss по обработанным позициям токенов", "Loss",
        "Обработанные позиции токенов, млн", train_series,
        lambda item, x, y: x * item["effective"] * SEQ_LENGTH,
    )
    write_png(
        ARTIFACTS / "eval_comparison.png", "Qwen3-1B: валидация на 5000 статьях", "Eval loss",
        "Шаги оптимизатора", eval_series,
    )
    for name in ("baseline_subset", "smoke_1000"):
        folder = ARTIFACTS / name
        history = json.loads((folder / "loss.json").read_text(encoding="utf-8"))
        write_png(
            folder / "loss.png", f"{name}: техническая проверка", "Loss", "Шаги оптимизатора",
            [
                {"label": "Train loss", "points": [(e["step"], e["loss"]) for e in history if "loss" in e]},
                {"label": "Eval loss", "points": [(e["step"], e["eval_loss"]) for e in history if "eval_loss" in e]},
            ],
        )


if __name__ == "__main__":
    main()
