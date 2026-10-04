from datasets import Dataset

import run_hw1
from preprocess import tokenize_function
from run_hw1 import load_training_config, prepare_tokenizer, train_model

# Two train blocks and one eval block, 512 tokens each.
# Two training steps see 1024 tokens, the closest fixed-size run to 1000.
TEXTS = [
    "Москва — столица России. Город расположен на реке Москва. " * 40,
    "Солнечная система состоит из Солнца и планет. " * 40,
    "В XIX веке развитие науки изменило представление о мире. " * 40,
]


def main():
    experiment_name, config, config_path = load_training_config("smoke_1000")
    tokenizer = prepare_tokenizer()
    tokenized = tokenize_function({"text": TEXTS}, tokenizer)
    tiny_dataset = Dataset.from_dict({
        "input_ids": tokenized["input_ids"],
        "attention_mask": tokenized["attention_mask"],
        "labels": tokenized["labels"],
    })
    token_count = sum(sum(mask) for mask in tiny_dataset["attention_mask"])
    print(f"Smoke dataset rows: {len(tiny_dataset)}, real tokens: {token_count}")

    def tiny_load(data_dir=None):
        return tiny_dataset

    def tiny_split(dataset, validation_size=1):
        return dataset.select([0, 1]), dataset.select([2])

    run_hw1.load_tokenized_dataset = tiny_load
    run_hw1.split_dataset = tiny_split
    train_model(config, experiment_name, config_path)


if __name__ == "__main__":
    main()
