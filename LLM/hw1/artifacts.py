import csv
import json
import math
import os

import torch
from preprocess import MAX_LENGTH, TOKENIZER_NAME, VALIDATION_SIZE


ARTIFACTS_ROOT = "artifacts"
GENERATION_PROMPTS = [
    "Тильзитский мир - ",
    "Деревня Сно - ",
    "14 восьмитысячников - ",
    "Евразийство становится - ",
]
GENERATION_CONFIG = {
    "max_new_tokens": 128,
    "do_sample": True,
    "temperature": 0.8,
    "top_p": 0.95,
}


def artifact_dir(experiment_name, artifacts_root=ARTIFACTS_ROOT):
    return os.path.join(artifacts_root, experiment_name)


def dump_json(path, payload):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        file.write("\n")


def loss_rows(log_history):
    rows = []
    for entry in log_history:
        if "loss" not in entry and "eval_loss" not in entry:
            continue
        rows.append({
            "step": entry.get("step"),
            "epoch": entry.get("epoch"),
            "learning_rate": entry.get("learning_rate"),
            "loss": entry.get("loss"),
            "eval_loss": entry.get("eval_loss"),
        })
    return rows


def write_loss_plot(rows, path):
    series = {
        "train loss": [(row["step"], row["loss"]) for row in rows if row["loss"] is not None],
        "eval loss": [(row["step"], row["eval_loss"]) for row in rows if row["eval_loss"] is not None],
    }
    points = [point for values in series.values() for point in values]
    if not points:
        return
    width, height, pad = 800, 400, 48
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if max_x == min_x:
        max_x += 1
    if max_y == min_y:
        max_y += 1

    def project(x, y):
        px = pad + (x - min_x) / (max_x - min_x) * (width - 2 * pad)
        py = height - pad - (y - min_y) / (max_y - min_y) * (height - 2 * pad)
        return px, py

    colors = {"train loss": "#1f77b4", "eval loss": "#d62728"}
    polylines = []
    legend = []
    for index, (name, values) in enumerate(series.items()):
        if not values:
            continue
        coords = " ".join(f"{project(x, y)[0]:.1f},{project(x, y)[1]:.1f}" for x, y in values)
        polylines.append(
            f'<polyline fill="none" stroke="{colors[name]}" stroke-width="2" points="{coords}"/>'
        )
        legend.append(
            f'<text x="{pad}" y="{20 + index * 16}" fill="{colors[name]}" font-size="14">{name}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        '<rect width="100%" height="100%" fill="white"/>'
        + "".join(polylines)
        + "".join(legend)
        + "</svg>\n"
    )
    with open(path, "w", encoding="utf-8") as file:
        file.write(svg)


def prepare_artifact_dir(experiment_name, training_config, config_path):
    """Create the experiment folder, or reuse it when this run already has one."""
    output_dir = artifact_dir(experiment_name)
    existed = os.path.isdir(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    dump_json(os.path.join(output_dir, "config.json"), {
        "experiment_name": experiment_name,
        "config_path": config_path,
        "training_config": training_config,
    })
    if existed:
        print(f"Artifacts already exist, reusing {output_dir}")
    else:
        print(f"Created {output_dir}")
    return output_dir


def build_run_trace(trainer, train_wall_seconds, training_config, final_eval_seconds=0.0):
    """Split the 15-minute loop into train time, validation time, steps, and tokens seen."""
    eval_seconds = 0.0
    eval_runs = 0
    for entry in trainer.state.log_history:
        if "eval_runtime" not in entry or "train_runtime" in entry:
            continue
        eval_seconds += float(entry["eval_runtime"])
        eval_runs += 1
    total_seconds = float(train_wall_seconds)
    train_seconds = max(total_seconds - eval_seconds, 0.0)
    optimizer_steps = int(trainer.state.global_step)
    per_device = int(training_config["per_device_train_batch_size"])
    accumulation = int(training_config.get("gradient_accumulation_steps", 1))
    microbatches = optimizer_steps * accumulation
    tokens_seen = microbatches * per_device * MAX_LENGTH
    return {
        "train_seconds": train_seconds,
        "eval_seconds": eval_seconds,
        "eval_runs_during_training": eval_runs,
        "total_seconds": total_seconds,
        "eval_fraction": (eval_seconds / total_seconds) if total_seconds else 0.0,
        "final_eval_seconds": float(final_eval_seconds),
        "optimizer_steps": optimizer_steps,
        "microbatches": microbatches,
        "tokens_seen": tokens_seen,
        "seq_length": MAX_LENGTH,
        "per_device_train_batch_size": per_device,
        "gradient_accumulation_steps": accumulation,
        "effective_batch_size": per_device * accumulation,
    }


def save_experiment_artifacts(
    trainer,
    eval_loss,
    perplexity,
    output_dir,
    experiment_name,
    training_config,
    config_path=None,
    train_wall_seconds=None,
    final_eval_seconds=0.0,
):
    """Write config, loss history, and final metrics for one experiment."""
    os.makedirs(output_dir, exist_ok=True)
    history = trainer.state.log_history
    rows = loss_rows(history)
    dump_json(os.path.join(output_dir, "config.json"), {
        "experiment_name": experiment_name,
        "config_path": config_path,
        "tokenizer_name": TOKENIZER_NAME,
        "max_length": MAX_LENGTH,
        "validation_size": VALIDATION_SIZE,
        "training_config": training_config,
        "generation_config": GENERATION_CONFIG,
        "generation_prompts": GENERATION_PROMPTS,
        "model_config": trainer.model.config.to_dict(),
    })
    dump_json(os.path.join(output_dir, "loss.json"), history)
    with open(os.path.join(output_dir, "loss.csv"), "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["step", "epoch", "learning_rate", "loss", "eval_loss"],
        )
        writer.writeheader()
        writer.writerows(rows)
    write_loss_plot(rows, os.path.join(output_dir, "loss.svg"))
    finite_perplexity = perplexity if math.isfinite(perplexity) else None
    dump_json(os.path.join(output_dir, "metrics.json"), {
        "eval_loss": float(eval_loss),
        "perplexity": finite_perplexity,
    })
    if train_wall_seconds is not None:
        trace = build_run_trace(
            trainer,
            train_wall_seconds,
            training_config,
            final_eval_seconds,
        )
        dump_json(os.path.join(output_dir, "trace.json"), trace)
        print(
            f"Train {trace['train_seconds']:.1f}s, "
            f"eval {trace['eval_seconds']:.1f}s ({trace['eval_fraction']:.1%} of the loop), "
            f"optimizer steps {trace['optimizer_steps']}, "
            f"microbatches {trace['microbatches']}, "
            f"tokens seen {trace['tokens_seen']}"
        )
    plot_comparison(os.path.dirname(output_dir))
    print(f"Saved experiment artifacts to {output_dir}")


def comparison_runs(artifacts_root=ARTIFACTS_ROOT):
    runs = []
    if not os.path.isdir(artifacts_root):
        return runs
    for name in sorted(os.listdir(artifacts_root)):
        folder = os.path.join(artifacts_root, name)
        loss_path = os.path.join(folder, "loss.json")
        config_path = os.path.join(folder, "config.json")
        if not os.path.isfile(loss_path) or not os.path.isfile(config_path):
            continue
        with open(loss_path, encoding="utf-8") as file:
            history = json.load(file)
        with open(config_path, encoding="utf-8") as file:
            saved = json.load(file)
        training_config = saved.get("training_config", {})
        per_device = training_config.get("per_device_train_batch_size", "?")
        accumulation = training_config.get("gradient_accumulation_steps", 1)
        learning_rate = training_config.get("learning_rate", "?")
        scheduler = training_config.get("lr_scheduler_type", "linear")
        effective = per_device * accumulation if isinstance(per_device, int) else "?"
        train_points = [
            (entry["step"], entry["loss"])
            for entry in history
            if "loss" in entry and "eval_loss" not in entry and "train_runtime" not in entry
        ]
        eval_points = [
            (entry["step"], entry["eval_loss"])
            for entry in history
            if "eval_loss" in entry
        ]
        metrics_path = os.path.join(folder, "metrics.json")
        final_eval = None
        if os.path.isfile(metrics_path):
            with open(metrics_path, encoding="utf-8") as file:
                final_eval = json.load(file).get("eval_loss")
        runs.append({
            "name": name,
            "label": (
                f"{name} (batch={effective}, lr={learning_rate}, {scheduler})"
            ),
            "train": train_points,
            "eval": eval_points,
            "final_eval": final_eval,
            "last_step": train_points[-1][0] if train_points else None,
        })
    real_runs = [run for run in runs if not run["name"].startswith("smoke")]
    return real_runs or runs


def plot_comparison(artifacts_root=ARTIFACTS_ROOT, output_path=None):
    """Overlay train-loss curves from finished experiments, with eval markers."""
    runs = [run for run in comparison_runs(artifacts_root) if run["train"]]
    output_path = output_path or os.path.join(artifacts_root, "comparison.svg")
    if not runs:
        return None
    width, height = 960, 560
    left, right, top, bottom = 70, 280, 50, 50
    points = [point for run in runs for point in run["train"]]
    points += [point for run in runs for point in run["eval"]]
    for run in runs:
        if run["final_eval"] is not None and run["last_step"] is not None:
            points.append((run["last_step"], run["final_eval"]))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if max_x == min_x:
        max_x += 1
    if max_y == min_y:
        max_y += 1
    pad_y = (max_y - min_y) * 0.05
    min_y -= pad_y
    max_y += pad_y

    def project(x, y):
        px = left + (x - min_x) / (max_x - min_x) * (width - left - right)
        py = height - bottom - (y - min_y) / (max_y - min_y) * (height - top - bottom)
        return px, py

    colors = ["#7f7f7f", "#ff7f0e", "#1f77b4", "#2ca02c", "#d62728", "#9467bd"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16">'
        "Сравнение сходимости претрейна Qwen3-1B за 15 минут (A100)</text>",
        f'<text x="24" y="{height / 2}" transform="rotate(-90 24 {height / 2})" '
        'text-anchor="middle" font-size="14">Train Loss</text>',
        f'<text x="{(left + width - right) / 2}" y="{height - 12}" text-anchor="middle" '
        'font-size="14">Шаги оптимизации</text>',
    ]
    for index, run in enumerate(runs):
        color = colors[index % len(colors)]
        coords = " ".join(
            f"{project(x, y)[0]:.1f},{project(x, y)[1]:.1f}" for x, y in run["train"]
        )
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{coords}"/>'
        )
        for x, y in run["eval"]:
            px, py = project(x, y)
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{color}"/>')
        if run["final_eval"] is not None and run["last_step"] is not None:
            px, py = project(run["last_step"], run["final_eval"])
            parts.append(
                f'<rect x="{px - 4:.1f}" y="{py - 4:.1f}" width="8" height="8" fill="{color}"/>'
            )
        legend_y = top + index * 22
        parts.append(
            f'<line x1="{width - right + 16}" y1="{legend_y}" x2="{width - right + 40}" '
            f'y2="{legend_y}" stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{width - right + 48}" y="{legend_y + 4}" font-size="12">{run["label"]}</text>'
        )
    parts.append("</svg>\n")
    os.makedirs(artifacts_root, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("".join(parts))
    print(f"Saved comparison plot to {output_path}")
    return output_path


def test_infer_model(model, tokenizer, device="cuda" if torch.cuda.is_available() else "cpu", output_dir=None):
    """Generate a continuation for each prompt and save the prompt with the result."""
    output_dir = output_dir or ARTIFACTS_ROOT
    os.makedirs(output_dir, exist_ok=True)
    model.config.use_cache = True
    model.to(device)
    model.eval()
    samples = []
    for prompt in GENERATION_PROMPTS:
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {name: value.to(device) for name, value in inputs.items()}
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                **GENERATION_CONFIG,
            )
        prompt_length = inputs["input_ids"].shape[1]
        completion = tokenizer.decode(output_ids[0, prompt_length:], skip_special_tokens=True)
        samples.append({
            "prompt": prompt,
            "completion": completion,
            "text": prompt + completion,
        })
        print(f"Prompt: {prompt}")
        print(f"Completion: {completion}")
    dump_json(os.path.join(output_dir, "generations.json"), samples)
    with open(os.path.join(output_dir, "generations.txt"), "w", encoding="utf-8") as file:
        for sample in samples:
            file.write(f"PROMPT: {sample['prompt']}\n")
            file.write(f"COMPLETION: {sample['completion']}\n\n")
    print(f"Saved generations to {output_dir}")
    return samples
