import glob
import json
import math
import os
import shutil
import sys
import pyarrow as pa
import pyarrow.parquet as pq
from artifacts import prepare_artifact_dir, save_experiment_artifacts, test_infer_model
from datasets import Dataset, load_dataset
from preprocess import (
    NUM_SHARDS,
    OUTPUT_DIR,
    VALIDATION_SIZE,
    prepare_tokenizer,
    tokenized_dataset_ready,
)
from transformers import (
    Qwen3Config,
    Qwen3ForCausalLM,
    Trainer,
    TrainingArguments,
    TrainerCallback,
    default_data_collator,
)
import torch
import time


# Don't change this parameter
MAX_TRAINING_TIME_SECONDS = 60 * 15
CONFIGS_DIR = "configs"
DEFAULT_CONFIG = "baseline"
CHECK_TRAIN_SIZE = 1000
CHECK_VAL_SIZE = 200
CHECK_TEST_SIZE = 100


class TimeoutCallback(TrainerCallback):
    """Callback to stop training after a specified timeout."""
    def __init__(self, timeout_seconds):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
    
    def on_train_begin(self, args, state, control, **kwargs):
        self.start_time = time.time()
    
    def on_step_end(self, args, state, control, **kwargs):
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            if elapsed > self.timeout_seconds:
                control.should_training_stop = True
                # Include the final weights in best-checkpoint selection.
                control.should_evaluate = True
                control.should_save = True
                print(f"Training stopped after {elapsed:.2f} seconds")
        return control


def resolve_config_path(name_or_path):
    if os.path.isfile(name_or_path):
        return name_or_path
    candidate = name_or_path if name_or_path.endswith(".json") else f"{name_or_path}.json"
    path = candidate if os.path.dirname(candidate) else os.path.join(CONFIGS_DIR, candidate)
    if os.path.isfile(path):
        return path
    raise FileNotFoundError(f"Training config not found: {name_or_path}")


def load_training_config(name_or_path):
    path = os.path.abspath(resolve_config_path(name_or_path))
    with open(path, encoding="utf-8") as file:
        config = json.load(file)
    experiment_name = os.path.splitext(os.path.basename(path))[0]
    return experiment_name, config, path


def ensure_tokenized_dataset(data_dir=OUTPUT_DIR):
    """Require the dataset already downloaded and tokenized by preprocess.py."""
    if tokenized_dataset_ready(data_dir, NUM_SHARDS):
        print(f"Tokenized dataset is ready in {data_dir}")
        return
    raise FileNotFoundError(
        f"Tokenized dataset is missing in {data_dir}. Run once: python preprocess.py"
    )


def parquet_shard_paths(data_dir=OUTPUT_DIR):
    return [
        os.path.join(data_dir, filename)
        for filename in sorted(os.listdir(data_dir))
        if filename.endswith(".parquet")
        and os.path.isfile(os.path.join(data_dir, filename))
    ]


def load_tokenized_dataset(data_dir=OUTPUT_DIR):
    """Load the parquet shards as a memory-mapped dataset, in filename order."""
    ensure_tokenized_dataset(data_dir)
    parquet_files = sorted(glob.glob(os.path.join(data_dir, "*.parquet")))
    print(f"Loading {len(parquet_files)} parquet shards...")
    return load_dataset("parquet", data_files=parquet_files, split="train")


def load_check_splits(data_dir=OUTPUT_DIR):
    """Read one shard and cut 1000 train / 200 val / 100 test out of the real split."""
    ensure_tokenized_dataset(data_dir)
    first_shard = parquet_shard_paths(data_dir)[0]
    table = pq.read_table(first_shard, memory_map=True)
    needed = VALIDATION_SIZE + CHECK_TRAIN_SIZE
    if table.num_rows < needed:
        raise RuntimeError(f"{first_shard} has {table.num_rows} rows, need {needed}")
    test_dataset = Dataset(table.slice(0, CHECK_TEST_SIZE))
    val_dataset = Dataset(table.slice(CHECK_TEST_SIZE, CHECK_VAL_SIZE))
    train_dataset = Dataset(table.slice(VALIDATION_SIZE, CHECK_TRAIN_SIZE))
    print(f"Check split from {first_shard}")
    print(f"Test rows 0:{CHECK_TEST_SIZE}: {len(test_dataset)}")
    print(f"Val rows {CHECK_TEST_SIZE}:{CHECK_TEST_SIZE + CHECK_VAL_SIZE}: {len(val_dataset)}")
    print(f"Train rows {VALIDATION_SIZE}:{VALIDATION_SIZE + CHECK_TRAIN_SIZE}: {len(train_dataset)}")
    return train_dataset, val_dataset, test_dataset


def split_dataset(dataset, validation_size=VALIDATION_SIZE):
    dataset_size = len(dataset)
    train_dataset = dataset.select(range(validation_size, dataset_size))
    eval_dataset = dataset.select(range(validation_size))
    
    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(eval_dataset)}")
    
    return train_dataset, eval_dataset


def create_model(tokenizer):
    # Don't change this parameter
    MODEL_CONFIG = {
        'hidden_size': 2048,
        'num_hidden_layers': 12,
        'num_attention_heads': 16,
        'num_key_value_heads': 8,
        'intermediate_size': 8192,
        'head_dim': 128,
        'hidden_act': 'silu',
        'initializer_range': 0.02,
        'scale_attn_weights': True,
        'use_cache': True,
    }

    config = Qwen3Config(
        vocab_size=tokenizer.vocab_size,
        bos_token_id=tokenizer.bos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
        **MODEL_CONFIG
    )
    
    model = Qwen3ForCausalLM._from_config(
        config,
        attn_implementation='flash_attention_2',
        torch_dtype=torch.bfloat16
    )
    
    print(f"Model pad token id: {model.config.pad_token_id}")
    
    with torch.no_grad():
        total_params = sum(p.numel() for p in model.parameters())
        print(f"Total params: {total_params:,}")
    
    return model


def remove_saved_weights(output_dir):
    """Drop checkpoint weights. Eval and generation already used the model in memory."""
    if not output_dir or not os.path.isdir(output_dir):
        return
    for name in os.listdir(output_dir):
        path = os.path.join(output_dir, name)
        if os.path.isdir(path) and (name == "best_model" or name.startswith("checkpoint-")):
            shutil.rmtree(path)
            print(f"Removed weights {path}")


def train_model(config, experiment_name, config_path, subset=False):
    """
    TODO: Implement the training pipeline.
    - Prepare tokenizer
    - Load tokenized dataset and split it
    - Create the model
    - Create TrainingArguments from config
    - Create Trainer with TimeoutCallback
    - Train the model
    - Run final evaluation and print results
    - Save metric history to trainer_state.json for local loss plots
    """
    if subset:
        experiment_name = f"{experiment_name}_subset"
        config = dict(config)
        config["output_dir"] = os.path.join(OUTPUT_DIR, experiment_name)
        config["eval_strategy"] = "steps"
        config["save_strategy"] = "steps"
        config["eval_steps"] = 10
        config["save_steps"] = 10
        config["logging_steps"] = 1
    run_dir = prepare_artifact_dir(experiment_name, config, config_path)
    tokenizer = prepare_tokenizer()
    if subset:
        train_dataset, eval_dataset, test_dataset = load_check_splits()
    else:
        dataset = load_tokenized_dataset()
        train_dataset, eval_dataset = split_dataset(dataset, VALIDATION_SIZE)
        test_dataset = eval_dataset
    model = create_model(tokenizer)
    training_args = TrainingArguments(**config)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
        callbacks=[TimeoutCallback(timeout_seconds=MAX_TRAINING_TIME_SECONDS)] # dont change
        )
    train_started = time.perf_counter()
    trainer.train()
    train_wall_seconds = time.perf_counter() - train_started
    print("Running final evaluation on the test split...")
    eval_results = trainer.evaluate(test_dataset)
    print(f"Final evaluation results: {eval_results}")

    eval_loss = eval_results.get("eval_loss", float("nan"))
    perplexity = math.exp(eval_loss) if eval_loss < 20 else float("inf")
    print(f"Final Eval Loss: {eval_loss:.4f} | Perplexity: {perplexity:.2f}")

    trainer.save_state()
    save_experiment_artifacts(
        trainer,
        eval_loss,
        perplexity,
        run_dir,
        experiment_name,
        config,
        config_path,
        train_wall_seconds,
        float(eval_results.get("eval_runtime") or 0.0),
    )
    test_infer_model(
        model,
        tokenizer,
        device="cuda" if torch.cuda.is_available() else "cpu",
        output_dir=run_dir,
    )
    remove_saved_weights(config["output_dir"])


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--subset"]
    subset = "--subset" in sys.argv
    config_name = args[0] if args else DEFAULT_CONFIG
    experiment_name, training_config, config_path = load_training_config(config_name)
    ensure_tokenized_dataset()
    train_model(training_config, experiment_name, config_path, subset=subset)