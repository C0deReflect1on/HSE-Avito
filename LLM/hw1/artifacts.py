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
    from plot_logs import write_png

    write_png(
        path, "Обучение и валидация", "Loss", "Шаги оптимизатора",
        [{"label": name, "points": values} for name, values in series.items()],
    )


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
    training_history = history[:next(i for i, entry in enumerate(history) if "train_runtime" in entry)]
    write_loss_plot(loss_rows(training_history), os.path.join(output_dir, "loss.png"))
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
        history = history[:next(i for i, entry in enumerate(history) if "train_runtime" in entry)]
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
            "best_step": min(eval_points, key=lambda point: point[1])[0] if eval_points else None,
        })
    real_runs = [run for run in runs if not run["name"].startswith("smoke") and not run["name"].endswith("_subset")]
    return real_runs or runs


def plot_comparison(artifacts_root=ARTIFACTS_ROOT, output_path=None):
    """Overlay train-loss curves from finished experiments, with eval markers."""
    runs = [run for run in comparison_runs(artifacts_root) if run["train"]]
    output_path = output_path or os.path.join(artifacts_root, "comparison.png")
    if not runs:
        return None
    from plot_logs import write_png

    os.makedirs(artifacts_root, exist_ok=True)
    write_png(
        output_path, "Qwen3-1B: обучение и валидация", "Loss", "Шаги оптимизатора",
        [{
            "label": run["label"], "points": run["train"], "marks": run["eval"],
            "marker": run["final_eval"], "marker_x": run["best_step"],
        } for run in runs],
    )
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
