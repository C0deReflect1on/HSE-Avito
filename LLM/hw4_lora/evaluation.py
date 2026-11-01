import torch
from rouge_score import rouge_scorer

HISTORY_SYSTEM_PROMPT = (
    "Answer the history question. Return only the letter of the correct option."
)


def make_history_messages(example):
    messages = [
        {"role": "system", "content": HISTORY_SYSTEM_PROMPT},
        {"role": "user", "content": example["question"] + "\n" + "\n".join(example["options"])},
    ]
    return messages


def generate_answers(
    model, tokenizer, prompts, generation_config, *, batch_size=1
):
    model.eval()
    tokenizer.padding_side = "left"
    answers = []

    with torch.inference_mode():
        for i in range(0, len(prompts), batch_size):
            inputs = prompts[i:i + batch_size]

            inputs = tokenizer.apply_chat_template(
                inputs,
                tokenize=True,
                add_generation_prompt=True,
                padding=True,
                return_tensors="pt",
                return_dict=True,
            )
            inputs = inputs.to(model.device)

            _answers = model.generate(
                **inputs,
                **generation_config,
            )

            _answers = _answers[:, inputs["input_ids"].shape[1]:]

            answers.extend(
                tokenizer.batch_decode(
                    _answers,
                    skip_special_tokens=True,
                )
            )

    return answers



def rouge_l(predictions, references):
    """Средний ROUGE-L F1 ответов WikiWhy относительно эталонов.

    Вход: непустые списки строк одинаковой длины в формате Answer/Explanation.
    Выход: float в [0, 1], без умножения на 100. Каждый пример имеет
    одинаковый вес. RougeScorer использует стандартную токенизацию
    и английский стемминг через use_stemmer=True.
    ROUGE-L оценивает текстовое совпадение через общую подпоследовательность
    токенов. Истинность причинного объяснения оценивается отдельно вручную.
    """
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    total = 0.0
    for prediction, reference in zip(predictions, references):
        scores = scorer.score(
            target=reference,
            prediction=prediction,
        )
        total += scores["rougeL"].fmeasure

    return total / len(predictions)

def parse_choice(text, choices):
    """Извлечение одной допустимой буквы ответа или None при нарушении формата.

    choices определяет допустимые буквы A, B, ... по числу вариантов вопроса.
    После удаления внешних пробелов и перевода в верхний регистр принимается
    ровно одна допустимая буква. Объяснение, несколько букв или буква вне
    списка дают None.
    """
    valid_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:len(choices)]
    text = text.strip().upper()

    if len(text) == 1 and text in valid_letters:
        return text

    return None



def history_accuracy(predictions, references):
    """Доля правильных ответов на внешнем историческом тесте в [0, 1].

    Вход: непустые списки одинаковой длины. predictions содержит буквы
    или None после parse_choice; references — правильные буквы answer.
    None считается ошибкой и остаётся в знаменателе. Сравнение моделей
    проводится на одинаковых вопросах. Метрика оценивает исторический
    экзамен отдельно от качества свободных объяснений WikiWhy.
    """
    result = [
        True if predictions[i] == references[i] else False
        for i in range(len(predictions))
    ]

    return sum(result)/len(result)