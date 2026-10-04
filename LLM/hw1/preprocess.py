import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("HF_HOME", os.path.join(ROOT, ".cache", "huggingface"))
os.environ.setdefault(
    "HF_DATASETS_CACHE",
    os.path.join(ROOT, ".cache", "huggingface", "datasets"),
)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from datasets import Features, Sequence, Value, load_dataset
from transformers import AutoTokenizer


MAX_LENGTH = 512
INPUT_IDS = "input_ids"
ATTENTION_MASK = "attention_mask"
LABELS = "labels"

TOKENIZER_NAME = "ai-forever/rugpt3small_based_on_gpt2"
OUTPUT_DIR = "./output_dir"
NUM_SHARDS = 32
VALIDATION_SIZE = 5000

DATASET_NAME = "wikimedia/wikipedia"
DATASET_CONFIG = "20231101.ru"
DATASET_SPLIT = "train"
META_FILENAME = "preprocess_meta.json"


def prepare_tokenizer():
    """
    TODO: Implement tokenizer preparation.
    - Load the tokenizer from TOKENIZER_NAME
    - Set pad_token to eos_token
    - Return the tokenizer
    """
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def tokenize_function(examples, tokenizer):
    """
    TODO: Implement tokenization function.
    - Tokenize the text with truncation and padding to MAX_LENGTH
    - Create labels from input_ids
    - Return dictionary with 'labels', 'input_ids', and 'attention_mask'
    """
    tokenized = tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        return_tensors=None,
    )
    tokenized[LABELS] = [
        [token if attn else -100 for token, attn in zip(ids, mask)]
        for ids, mask in zip(tokenized[INPUT_IDS], tokenized[ATTENTION_MASK])
    ]

    return {
        "input_ids": tokenized["input_ids"],
        "attention_mask": tokenized["attention_mask"],
        "labels": tokenized["labels"]
    }


def shard_paths(output_dir=OUTPUT_DIR, num_shards=NUM_SHARDS):
    return [
        os.path.join(output_dir, f"{index:05d}.parquet")
        for index in range(num_shards)
    ]


def meta_path(output_dir=OUTPUT_DIR):
    return os.path.join(output_dir, META_FILENAME)


def expected_meta(num_shards=NUM_SHARDS):
    return {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "tokenizer": TOKENIZER_NAME,
        "max_length": MAX_LENGTH,
        "validation_size": VALIDATION_SIZE,
        "num_shards": num_shards,
    }


def tokenized_dataset_ready(output_dir=OUTPUT_DIR, num_shards=NUM_SHARDS):
    path = meta_path(output_dir)
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as meta_file:
        meta = json.load(meta_file)
    expected = expected_meta(num_shards)
    if any(meta.get(key) != value for key, value in expected.items()):
        return False
    if not isinstance(meta.get("num_rows"), int) or meta["num_rows"] <= VALIDATION_SIZE:
        return False
    for shard in shard_paths(output_dir, num_shards):
        if not os.path.isfile(shard) or os.path.getsize(shard) == 0:
            return False
    return True


def save_as_parquets(ds, output_dir=OUTPUT_DIR, num_shards=NUM_SHARDS):
    """
    TODO: Implement saving dataset as parquet shards.
    - Create output directory if it doesn't exist
    - Split dataset into num_shards shards
    - Save each shard as a parquet file with format: {output_dir}/{index:05d}.parquet
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving dataset into {num_shards} shards in {output_dir}...")
    saved_rows = 0
    for index in range(num_shards):
        shard = ds.shard(num_shards=num_shards, index=index, contiguous=True)
        shard_path = os.path.join(output_dir, f"{index:05d}.parquet")
        shard.to_parquet(shard_path)
        saved_rows += shard.num_rows
        print(f"Saved {shard_path} ({shard.num_rows} rows)")
    if saved_rows != ds.num_rows:
        raise RuntimeError(
            f"Shard row count {saved_rows} does not match dataset length {ds.num_rows}"
        )
    print("Dataset successfully tokenized and saved as parquet files.")
    return saved_rows


def prepare_dataset():
    """
    TODO: Implement dataset preparation.
    - Load the Wikipedia dataset: "wikimedia/wikipedia", "20231101.ru", split="train"
    - Tokenize the dataset using tokenize_function
    - Save as parquet files
    """
    if tokenized_dataset_ready():
        print(f"Tokenized dataset already exists in {OUTPUT_DIR}")
        return

    stale_meta = meta_path()
    if os.path.isfile(stale_meta):
        os.remove(stale_meta)

    print("Loading raw Wikipedia dataset...")
    raw_dataset = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLIT)
    if len(raw_dataset) <= VALIDATION_SIZE:
        raise RuntimeError(
            f"Dataset has {len(raw_dataset)} rows, need more than {VALIDATION_SIZE}"
        )
    tokenizer = prepare_tokenizer()

    print("Tokenizing dataset across multiple CPU workers...")
    tokenized_dataset = raw_dataset.map(
        lambda examples: tokenize_function(examples, tokenizer),
        batched=True,
        batch_size=1000,
        num_proc=os.cpu_count() or 8,
        remove_columns=raw_dataset.column_names,
        features=Features({
            INPUT_IDS: Sequence(Value("int32")),
            ATTENTION_MASK: Sequence(Value("int8")),
            LABELS: Sequence(Value("int32")),
        }),
        desc="Tokenizing",
    )
    num_rows = save_as_parquets(tokenized_dataset, OUTPUT_DIR, NUM_SHARDS)
    meta = expected_meta()
    meta["num_rows"] = num_rows
    with open(meta_path(), "w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, indent=2)
        meta_file.write("\n")
    print(f"Rows: {num_rows}")
    print(f"Test set: first {VALIDATION_SIZE} rows")
    print(f"Train set: rows {VALIDATION_SIZE}..{num_rows - 1}")


if __name__ == "__main__":
    prepare_dataset()
