"""A short single-GPU GRPO run. Imports of training dependencies stay on the server."""

import argparse
import hashlib
import json
import math
import random
import time
from importlib.metadata import version
from pathlib import Path

from prepare import load_examples, render_prompt
from rewards import score_response

MODEL_ID = "Qwen/Qwen3.5-2B"
MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"


def load_tokenizer():
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def build_training_rows(examples, tokenizer, max_prompt_tokens):
    rows = []
    skipped = 0
    for messages, answer, tools in examples:
        prompt = render_prompt(messages, tools, tokenizer)
        tokens = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        if len(tokens) > max_prompt_tokens:
            skipped += 1
            continue
        # JSON strings preserve variable schemas and argument keys in Arrow datasets.
        rows.append({
            "prompt": prompt,
            "answer_json": json.dumps(answer, ensure_ascii=False),
            "tools_json": json.dumps(tools, ensure_ascii=False),
        })
    if not rows:
        raise ValueError("Не осталось примеров после ограничения длины prompt")
    return rows, skipped


def load_base_model():
    import torch
    from transformers import Qwen3_5ForCausalLM, Qwen3_5TextConfig

    config = Qwen3_5TextConfig.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model, loading = Qwen3_5ForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        config=config,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        output_loading_info=True,
    )
    if loading["missing_keys"]:
        raise RuntimeError(f"Не загружены веса языковой модели: {loading['missing_keys']}")
    return model


def make_training_reward(output_dir, weights, eos_token_ids, max_completion_length, num_generations):
    batch_id = 0

    def tool_call_reward(completions, answer_json, tools_json, completion_ids,
                         trainer_state, **kwargs):
        import torch

        nonlocal batch_id
        rewards = []
        rows = []
        for index, response in enumerate(completions):
            answer = json.loads(answer_json[index])
            tools = json.loads(tools_json[index])
            ids = completion_ids[index]
            truncated = len(ids) >= max_completion_length and ids[-1] not in eos_token_ids
            scores = score_response(response, answer, tools)
            if truncated:
                scores = {name: 0.0 for name in scores}
            total = sum(weights[name] * scores[name] for name in weights)
            if not math.isfinite(total):
                raise ValueError("Награда должна быть конечным числом")
            rewards.append(total)
            rows.append({
                "step": trainer_state.global_step,
                "batch": batch_id,
                "group": index // num_generations,
                "response": response,
                "answer": answer,
                "scores": scores,
                "reward": total,
                "completion_tokens": len(ids),
                "truncated": truncated,
                "gpu_allocated_gib": torch.cuda.memory_allocated() / 1024 ** 3,
            })
        with (output_dir / "generations.jsonl").open("a", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
        batch_id += 1
        return rewards

    return tool_call_reward


def run_training(data_path, config_path, output_dir):
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import set_seed
    from trl import GRPOConfig, GRPOTrainer

    if not torch.cuda.is_available():
        raise RuntimeError("Этот запуск требует CUDA GPU")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("Конфигурация использует bfloat16; нужен GPU с его поддержкой")
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Каталог уже содержит результаты: {output_dir}; выбери новый")
    settings = json.loads(Path(config_path).read_text())
    set_seed(settings["seed"])
    tokenizer = load_tokenizer()
    rows, skipped = build_training_rows(
        load_examples(data_path), tokenizer, settings["max_prompt_tokens"]
    )
    random.Random(settings["seed"]).shuffle(rows)
    rows = rows[:settings["dataset_limit"]]
    dataset = Dataset.from_list(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        **settings,
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "data_path": str(data_path),
        "data_sha256": hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
        "training_examples": len(rows),
        "skipped_long_prompts": skipped,
        "versions": {name: version(name) for name in ["torch", "transformers", "trl", "peft", "datasets"]},
    }
    (output_dir / "config.json").write_text(json.dumps(metadata, indent=2))
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    torch.cuda.reset_peak_memory_stats()
    model = load_base_model().to("cuda")
    lora = LoraConfig(
        task_type="CAUSAL_LM",
        r=settings["lora_rank"],
        lora_alpha=settings["lora_alpha"],
        lora_dropout=0.0,
        target_modules=settings["target_modules"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    eos_token_ids = model.generation_config.eos_token_id or []
    if isinstance(eos_token_ids, int):
        eos_token_ids = [eos_token_ids]
    eos_token_ids = set(eos_token_ids) | {tokenizer.eos_token_id}
    training_reward = make_training_reward(
        output_dir, settings["reward_weights"], eos_token_ids,
        settings["max_completion_length"], settings["num_generations"],
    )
    args = GRPOConfig(
        output_dir=str(output_dir),
        max_steps=settings["max_steps"],
        per_device_train_batch_size=settings["per_device_train_batch_size"],
        gradient_accumulation_steps=settings["gradient_accumulation_steps"],
        num_generations=settings["num_generations"],
        max_completion_length=settings["max_completion_length"],
        learning_rate=settings["learning_rate"],
        temperature=settings["temperature"],
        beta=settings["beta"],
        loss_type=settings["loss_type"],
        scale_rewards=settings["scale_rewards"],
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        mask_truncated_completions=True,
        use_vllm=False,
        lr_scheduler_type="constant",
        weight_decay=0.0,
        logging_steps=1,
        save_strategy="no",
        report_to="none",
        remove_unused_columns=False,
        seed=settings["seed"],
    )
    trainer = GRPOTrainer(
        model=model, args=args, reward_funcs=training_reward,
        train_dataset=dataset, processing_class=tokenizer,
    )
    before = {}
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            before[name] = parameter.detach().float().cpu().clone()
    torch.cuda.synchronize()
    start = time.perf_counter()
    trainer.train()
    torch.cuda.synchronize()
    train_seconds = time.perf_counter() - start
    changed = 0
    delta_squared = 0.0
    for name, parameter in model.named_parameters():
        if name in before:
            delta = parameter.detach().float().cpu() - before[name]
            changed += int(torch.count_nonzero(delta).item() > 0)
            delta_squared += delta.square().sum().item()
    if not math.isfinite(delta_squared):
        raise RuntimeError("Обновление весов содержит NaN или inf")
    trainer.save_model(str(output_dir / "adapter"))
    tokenizer.save_pretrained(output_dir / "adapter")
    (output_dir / "history.json").write_text(json.dumps(trainer.state.log_history, indent=2))
    generations = []
    for line in (output_dir / "generations.jsonl").read_text().splitlines():
        generations.append(json.loads(line))
    groups = {}
    for row in generations:
        key = (row["batch"], row["group"])
        groups.setdefault(key, []).append(row["reward"])
    varied_groups = sum(max(values) > min(values) for values in groups.values())
    logged_numbers = []
    for entry in trainer.state.log_history:
        for key in ("loss", "grad_norm", "reward"):
            if key in entry:
                logged_numbers.append(entry[key])
    finite_metrics = all(math.isfinite(value) for value in logged_numbers)
    summary = {
        "status": "updated" if changed and finite_metrics else "check_failed",
        "gpu": torch.cuda.get_device_name(),
        "gpu_total_gib": total_bytes / 1024 ** 3,
        "gpu_free_before_load_gib": free_bytes / 1024 ** 3,
        "peak_allocated_gib": torch.cuda.max_memory_allocated() / 1024 ** 3,
        "peak_reserved_gib": torch.cuda.max_memory_reserved() / 1024 ** 3,
        "train_seconds": train_seconds,
        "optimizer_steps": trainer.state.global_step,
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "changed_parameter_tensors": changed,
        "parameter_delta_l2": math.sqrt(delta_squared),
        "reward_groups": len(groups),
        "groups_with_reward_variation": varied_groups,
        "truncated_completions": sum(row["truncated"] for row in generations),
        "generated_completions": len(generations),
        "finite_training_metrics": finite_metrics,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def export_model(adapter_path, output_path):
    from peft import PeftModel

    model = PeftModel.from_pretrained(load_base_model(), adapter_path)
    model = model.merge_and_unload()
    model.save_pretrained(output_path)
    load_tokenizer().save_pretrained(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Короткий GRPO-запуск на одном GPU")
    parser.add_argument("--data", default="data/prepared/train.jsonl")
    parser.add_argument("--config", default="configs/smoke.json")
    parser.add_argument("--output", default="results/smoke")
    args = parser.parse_args()
    result = run_training(args.data, args.config, args.output)
    print(json.dumps(result, indent=2))
    if result["status"] != "updated":
        raise RuntimeError("Проверка обновления или метрик не прошла; смотри summary.json и generations.jsonl")
