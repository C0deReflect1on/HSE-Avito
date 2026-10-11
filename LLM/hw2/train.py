import argparse
import json
import math
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset, DatasetDict, load_dataset, load_from_disk
from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    PreTrainedTokenizerBase,
    Qwen3Config,
    Qwen3ForCausalLM,
    Trainer,
    TrainerCallback,
    TrainerControl,
    TrainerState,
    TrainingArguments,
    set_seed,
)
from transformers.utils import ModelOutput
from trl import SFTConfig, SFTTrainer
from trl.trainer.sft_trainer import DataCollatorForLanguageModeling


DATA: Path = Path("data")
TRAIN_SECONDS: float = 300
ATTENTION_IMPLEMENTATION: str = "sdpa"

MODEL_CONFIG: dict[str, Any] = dict(
    hidden_size=2048,
    num_hidden_layers=12,
    num_attention_heads=16,
    num_key_value_heads=8,
    intermediate_size=8192,
    head_dim=128,
    use_cache=False,
)

TRAINING_CONFIG: dict[str, Any] = dict(
    output_dir="results/baseline",
    # Настройки для экспериментов.
    per_device_train_batch_size=32,
    gradient_accumulation_steps=2,
    gradient_checkpointing=False,
    torch_compile=False,
    use_liger_kernel=False,
    activation_offloading=False,
    packing=False,
    padding_free=False,
    # Общие параметры обучения и замера.
    max_steps=1_000_000,
    learning_rate=3e-4,
    lr_scheduler_type="constant_with_warmup",
    warmup_steps=200,
    weight_decay=0.01,
    optim="adamw_torch_fused",
    bf16=True,
    tf32=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    packing_strategy="bfd",
    max_length=512,
    completion_only_loss=False,
    loss_type="nll",
    dataloader_num_workers=2,
    dataloader_pin_memory=True,
    logging_steps=10,
    logging_nan_inf_filter=False,
    report_to="none",
    save_strategy="no",
    eval_strategy="no",
    seed=42,
    data_seed=42,
    disable_tqdm=True,
)


def progress(stage: str, done: float, total: float, start: float) -> dict[str, Any]:
    elapsed = time.perf_counter() - start
    remaining = max(0.0, total - done) * elapsed / done if done else None
    return dict(
        phase=stage,
        elapsed_seconds=round(elapsed, 1),
        remaining_seconds=round(remaining, 1) if remaining is not None else None,
        eta=(datetime.now().astimezone() + timedelta(seconds=remaining)).isoformat(timespec="seconds")
        if remaining is not None else None,
    )


def prepare_data() -> None:
    started = time.perf_counter()
    print(json.dumps(dict(phase="prepare_data", status="started")), flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        "ai-forever/rugpt3small_based_on_gpt2",
        revision="a9307e696cd3c5b7f953ff4cb19d76a4d81821d5",
    )
    tokenizer.pad_token = tokenizer.eos_token
    source = load_dataset(
        "wikimedia/wikipedia",
        "20231101.ru",
        split="train",
        streaming=True,
        revision="b04c8d1ceb2f5cd4588862100d08de323dccfbaa",
    )
    rows: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for index, article in enumerate(source.take(50_500)):
        split = "validation" if index < 500 else "train"
        paragraphs = [
            p.strip() for p in article["text"].splitlines() if len(p.strip()) >= 80
        ][:8]
        if paragraphs:
            encoded = tokenizer(
                paragraphs,
                add_special_tokens=False,
                truncation=True,
                max_length=511,
                return_attention_mask=False,
            )["input_ids"]
            for paragraph_index, tokens in enumerate(encoded):
                if len(tokens) >= 32:
                    rows[split].append(
                        dict(
                            input_ids=tokens + [tokenizer.eos_token_id],
                            article_id=article["id"],
                            paragraph_index=paragraph_index,
                        )
                    )
        if (index + 1) % 5000 == 0:
            print(json.dumps(dict(progress("prepare_data", index + 1, 50_500, started), articles=index + 1)), flush=True)
    DatasetDict(
        {name: Dataset.from_list(items) for name, items in rows.items()}
    ).save_to_disk(str(DATA / "dataset"))
    tokenizer.save_pretrained(DATA / "tokenizer")
    print(json.dumps(dict(progress("prepare_data", 50_500, 50_500, started), status="finished")), flush=True)


class CausalCollator(DataCollatorForLanguageModeling):
    def torch_call(self, examples: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        batch = super().torch_call(examples)
        batch["labels"][:, 0] = -100
        return batch


class BenchmarkTrainer(SFTTrainer):
    target_tokens: torch.Tensor

    def compute_loss(
        self,
        model: torch.nn.Module,
        inputs: dict[str, Any],
        return_outputs: bool = False,
        num_items_in_batch: torch.Tensor | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, ModelOutput]:
        return Trainer.compute_loss(
            self,
            model,
            inputs,
            return_outputs=return_outputs,
            num_items_in_batch=num_items_in_batch,
        )

    def training_step(
        self,
        model: torch.nn.Module,
        inputs: dict[str, Any],
        num_items_in_batch: torch.Tensor | None = None,
    ) -> torch.Tensor:
        self.target_tokens += inputs["labels"].ne(-100).sum()
        return super().training_step(model, inputs, num_items_in_batch)

    def log(self, logs: dict[str, float], start_time: float | None = None) -> None:
        for key in ("loss", "grad_norm", "train_loss"):
            if key in logs and not math.isfinite(logs[key]):
                raise FloatingPointError(f"Значение {key} не валидное")
        logs.pop("train_samples_per_second", None)
        logs.pop("train_steps_per_second", None)
        super().log(logs, start_time)


class Benchmark(TrainerCallback):
    start: float
    previous_end: float
    previous_tokens: int

    def __init__(self, trainer: BenchmarkTrainer, seconds: float) -> None:
        self.trainer, self.seconds = trainer, seconds
        self.steps: list[dict[str, float | int | bool]] = []

    def on_train_begin(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        self.start = self.previous_end = time.perf_counter()
        self.last_progress = self.start
        self.previous_tokens = 0
        print(json.dumps(dict(phase="train", status="started", duration_seconds=self.seconds)), flush=True)

    def on_step_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        torch.cuda.synchronize()
        now = time.perf_counter()
        tokens = self.trainer.target_tokens.item()
        record: dict[str, float | int | bool] = dict(
            step=state.global_step,
            elapsed_seconds=now - self.start,
            step_seconds=now - self.previous_end,
            target_tokens=tokens - self.previous_tokens,
            warmup=state.global_step <= 10,
        )
        self.steps.append(record)
        if now - self.last_progress >= 10 or now - self.start >= self.seconds:
            print(json.dumps(dict(record, **progress("train", min(now - self.start, self.seconds), self.seconds, self.start))), flush=True)
            self.last_progress = now
        self.previous_end, self.previous_tokens = now, tokens
        if now - self.start >= self.seconds:
            control.should_training_stop = True

    def summary(self) -> dict[str, float | int | None]:
        measured = self.steps[10:]
        duration = sum(step["step_seconds"] for step in measured)
        tokens = sum(step["target_tokens"] for step in measured)
        elapsed = self.previous_end - self.start
        return dict(
            train_seconds=elapsed,
            optimizer_steps=len(self.steps),
            target_tokens=self.previous_tokens,
            tokens_per_second_including_warmup=self.previous_tokens / elapsed,
            warmup_steps=10,
            measured_steps=len(measured),
            measured_seconds=duration,
            tokens_per_second=tokens / duration if measured else None,
            seconds_per_optimizer_step=duration / len(measured) if measured else None,
            peak_allocated_gib=torch.cuda.max_memory_allocated() / 2**30,
            peak_reserved_gib=torch.cuda.max_memory_reserved() / 2**30,
        )


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    dataset: Dataset,
    tokenizer: PreTrainedTokenizerBase,
) -> dict[str, float | int]:
    started = time.perf_counter()
    print(json.dumps(dict(phase="validation", status="started")), flush=True)
    loader = DataLoader(
        dataset.select_columns(["input_ids"]),
        batch_size=8,
        collate_fn=CausalCollator(tokenizer.pad_token_id, completion_only_loss=False),
    )
    model.eval()
    loss_sum, tokens = 0.0, 0
    for index, batch in enumerate(loader, 1):
        batch = {key: value.cuda() for key, value in batch.items()}
        count = batch["labels"].ne(-100).sum().item()
        loss_sum += model(**batch).loss.item() * count
        tokens += count
        if index % 8 == 0 or index == len(loader):
            print(json.dumps(dict(progress("validation", index, len(loader), started), batches=index)), flush=True)
    loss = loss_sum / tokens
    if not math.isfinite(loss):
        raise FloatingPointError("Значение validation_loss не валидное")

    return dict(validation_loss=loss, validation_target_tokens=tokens)


class Tee:
    def __init__(self, *streams: Any) -> None:
        self.streams = streams

    def write(self, value: str) -> int:
        for stream in self.streams:
            stream.write(value)
            stream.flush()
        return len(value)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return self.streams[0].isatty()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Обучение и измерение скорости на одной GPU")
    parser.add_argument("--output-dir", default=TRAINING_CONFIG["output_dir"])
    parser.add_argument("--seconds", type=float, default=TRAIN_SECONDS)
    parser.add_argument("--batch-size", type=int, default=TRAINING_CONFIG["per_device_train_batch_size"])
    parser.add_argument("--gradient-accumulation-steps", type=int, default=TRAINING_CONFIG["gradient_accumulation_steps"])
    parser.add_argument("--attention", choices=("sdpa", "flash_attention_2"), default=ATTENTION_IMPLEMENTATION)
    parser.add_argument("--padding-free", action="store_true")
    parser.add_argument("--packing", action="store_true")
    args = parser.parse_args()
    if args.seconds <= 0 or args.batch_size <= 0 or args.gradient_accumulation_steps <= 0:
        parser.error("seconds, batch-size и gradient-accumulation-steps должны быть положительными")
    if (args.padding_free or args.packing) and args.attention != "flash_attention_2":
        parser.error("padding-free и BFD packing требуют FlashAttention 2")
    return args


def train(args: argparse.Namespace) -> None:
    training_config = dict(
        TRAINING_CONFIG,
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        padding_free=args.padding_free,
        packing=args.packing,
    )
    training_args = SFTConfig(**training_config)

    output = Path(training_args.output_dir)
    (output / "config.json").write_text(json.dumps(dict(
        train_seconds=args.seconds,
        attention_implementation=args.attention,
        model_config=MODEL_CONFIG,
        training_config=training_config,
        torch_version=torch.__version__,
        gpu_name=torch.cuda.get_device_name(),
        gpu_memory_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1),
    ), indent=2) + "\n")
    if not (DATA / "dataset").exists():
        prepare_data()
    tokenizer = AutoTokenizer.from_pretrained(DATA / "tokenizer")
    dataset = load_from_disk(str(DATA / "dataset"))

    set_seed(training_args.seed)
    config = Qwen3Config(
        vocab_size=tokenizer.vocab_size,
        bos_token_id=tokenizer.bos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
        **MODEL_CONFIG,
    )
    model = Qwen3ForCausalLM._from_config(
        config,
        attn_implementation=args.attention,
        torch_dtype=torch.bfloat16,
    )

    trainer = BenchmarkTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        processing_class=tokenizer,
        data_collator=(
            None
            if training_args.packing or training_args.padding_free
            else CausalCollator(tokenizer.pad_token_id)
        ),
    )
    trainer.target_tokens = torch.zeros((), dtype=torch.int64, device="cuda")
    benchmark = Benchmark(trainer, args.seconds)
    trainer.add_callback(benchmark)

    trainer.train()
    summary = benchmark.summary()
    summary.update(
        evaluate(trainer.model, dataset["validation"].select(range(512)), tokenizer)
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


def main() -> int:
    args = parse_args()
    output = Path(args.output_dir)
    if output.exists():
        raise FileExistsError(f"Каталог результата уже существует: {output}")
    output.mkdir(parents=True)
    with (output / "run.log").open("w", buffering=1) as log:
        with redirect_stdout(Tee(sys.stdout, log)), redirect_stderr(Tee(sys.stderr, log)):
            try:
                train(args)
            except Exception:
                traceback.print_exc()
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
