SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the question using the requested format: "
    "Answer: ... followed by Explanation: ..."
)


def make_prompt(example):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}, # каждый вопрос теста - новый диалог
        {"role": "user", "content": example["question"]},
    ]
    return messages


def make_target(example):
    return (
        f"Answer: {example['cause']}\n"
        f"Explanation: {example['explanation']}"
    )


def tokenize_example(example, tokenizer, *, max_length):
    messages = make_prompt(example)

    prompt_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
    )
    prompt_length = len(prompt_ids)

    messages.append({
        "role": "assistant",
        "content": make_target(example),
    })

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
    )

    labels = input_ids.copy()
    labels[:prompt_length] = [-100] * prompt_length

    input_ids = input_ids[:max_length]
    labels = labels[:max_length]

    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": labels,
    }