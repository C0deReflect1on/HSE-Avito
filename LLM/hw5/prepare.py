"""ToolACE parsing and dialogue-level preparation. No model weights are loaded."""

import argparse
import ast
import hashlib
import io
import json
import keyword
import random
import tokenize
from pathlib import Path
from typing import Any, TypedDict

TYPE_NAMES = {
    "dict": "object",
    "float": "number",
    "int": "integer",
}


class ToolCall(TypedDict):
    name: str
    arguments: dict[str, Any]


def parse_assitant_call(s: str, tool_names=None) -> list[ToolCall]:
    s = s.strip()
    if not s.startswith('['):
        return []
    if not s.endswith(']'):
        raise ValueError('Не закрыт список вызовов')

    s = s[1:-1].strip()
    tools = []
    while s:
        if tool_names is None:
            start = s.find('(')
            name = s[:start].strip()
        else:
            matches = [name for name in tool_names
                       if s.startswith(name) and s[len(name):].lstrip().startswith('(')]
            if not matches:
                raise ValueError('Вызов не совпал с доступными именами функций')
            name = max(matches, key=len)
            start = s.find('(', len(name))
        if start <= 0:
            raise ValueError('Ожидалось имя функции и скобка')
        depth, quote, escaped = 1, None, False
        for end in range(start + 1, len(s)):
            char = s[end]
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in ('"', "'"):
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    break
        else:
            raise ValueError('Не закрыта скобка или строка')

        # Имя с пробелами заменяется только для разбора аргументов.
        expression = 'f' + s[start:end + 1]
        tokens = list(tokenize.generate_tokens(io.StringIO(expression).readline))
        aliases = {}
        normalized_tokens = []
        # from= допустим в ToolACE, но является ключевым словом Python.
        for index, token in enumerate(tokens):
            text = token.string
            if (token.type == tokenize.NAME and keyword.iskeyword(text)
                    and tokens[index + 1].string == '='):
                alias = f'__toolace_{text}'
                if alias in expression:
                    raise ValueError('Конфликт временного имени аргумента')
                aliases[alias] = text
                text = alias
            normalized_tokens.append((token.type, text))
        call = ast.parse(tokenize.untokenize(normalized_tokens), mode='eval').body
        if not isinstance(call, ast.Call) or call.args:
            raise ValueError('Ожидались только именованные аргументы')
        arguments = {}
        for argument in call.keywords:
            arg_name = aliases.get(argument.arg, argument.arg)
            if arg_name is None or arg_name in arguments:
                raise ValueError('Распаковка или повтор аргумента')
            arguments[arg_name] = ast.literal_eval(argument.value)
        tools.append({'name': name, 'arguments': arguments})

        s = s[end + 1:].strip()
        if s:
            if not s.startswith(','):
                raise ValueError('Между вызовами нужна запятая')
            s = s[1:].strip()
    return tools


def convert_schema(value):
    if isinstance(value, list):
        return [convert_schema(item) for item in value]

    if not isinstance(value, dict):
        return value

    result = {}

    for key, item in value.items():
        if key == "type" and isinstance(item, str):
            result[key] = TYPE_NAMES.get(item, item)
        else:
            result[key] = convert_schema(item)

    return result


def parse_tools(system_text):
    marker = 'Here is a list of functions in JSON format that you can invoke:'
    marker_position = system_text.find(marker)

    if marker_position == -1:
        raise ValueError('Не найдено начало описаний инструментов')

    tools_start = marker_position + len(marker)
    tools_text = system_text[tools_start:].lstrip()
    raw_tools, _ = json.JSONDecoder().raw_decode(tools_text)

    tools = []
    for raw_tool in raw_tools:
        function = {
            'name': raw_tool['name'],
            'description': raw_tool['description'],
            'parameters': convert_schema(raw_tool['parameters']),
        }
        tools.append({
            'type': 'function',
            'function': function,
        })

    return tools


def parse_dialogue(row, dialogue_id):
    tools = parse_tools(row['system'])
    tool_names = {tool['function']['name'] for tool in tools}

    messages = []
    targets = []
    for index, message in enumerate(row['conversations']):
        role = message['from']
        text = message['value']
        if role not in {'user', 'assistant', 'tool'}:
            raise ValueError(f'Неизвестная роль: {role}')

        converted_message = {
            'role': role,
            'content': text,
        }
        if role == 'assistant':
            if not text.strip():
                raise ValueError(f'Пустая реплика assistant: {index}')

            calls = parse_assitant_call(text, tool_names)
            unknown_names = set()

            for call in calls:
                if call['name'] not in tool_names:
                    unknown_names.add(call['name'])
            if unknown_names:
                raise ValueError(f'Неизвестные функции: {sorted(unknown_names)}')

            if calls:
                converted_message['content'] = ''
                converted_message['tool_calls'] = []
                for call in calls:
                    converted_message['tool_calls'].append({
                        'type': 'function',
                        'function': call,
                    })

            targets.append({
                'message_index': index,
                'text': text,
                'calls': calls,
            })
        messages.append(converted_message)

    return {
        'dialogue_id': dialogue_id,
        'tools': tools,
        'messages': messages,
        'targets': targets,
    }


def make_rl_examples(dialogues):
    examples = []

    for dialogue in dialogues:
        messages = dialogue['messages']

        for i, message in enumerate(messages):
            if message['role'] == 'assistant':
                prompt = messages[:i]
                answer = message
                tools = dialogue['tools']
                examples.append((prompt, answer, tools))

    return examples


def parse_dialogues(rows):
    dialogues = []
    errors = []
    for dialogue_id, row in enumerate(rows):
        try:
            dialogues.append(parse_dialogue(row, dialogue_id))
        except (ValueError, SyntaxError, KeyError, TypeError, tokenize.TokenError) as error:
            errors.append({"dialogue_id": dialogue_id, "reason": str(error)})
    return dialogues, errors


def split_dialogues(dialogues, seed=42, validation_fraction=0.1):
    shuffled = dialogues.copy()
    random.Random(seed).shuffle(shuffled)
    validation_size = round(len(shuffled) * validation_fraction)
    if validation_size == 0 or validation_size == len(shuffled):
        raise ValueError("Нужны непустые train и validation; увеличь число диалогов")
    return shuffled[validation_size:], shuffled[:validation_size]


def render_prompt(messages, tools, tokenizer):
    return tokenizer.apply_chat_template(
        messages,
        tools=tools,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def save_examples(examples, path):
    with Path(path).open("w", encoding="utf-8") as file:
        for messages, answer, tools in examples:
            row = {"messages": messages, "answer": answer, "tools": tools}
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_examples(path):
    examples = []
    with Path(path).open(encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            examples.append((row["messages"], row["answer"], row["tools"]))
    return examples


def prepare_data(input_path, output_dir, limit=None, seed=42):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    with input_path.open(encoding="utf-8") as file:
        rows = json.load(file)
    if limit is not None:
        rows = rows[:limit]

    dialogues, errors = parse_dialogues(rows)
    train_dialogues, validation_dialogues = split_dialogues(dialogues, seed)
    train = make_rl_examples(train_dialogues)
    validation = make_rl_examples(validation_dialogues)
    train_ids = {dialogue["dialogue_id"] for dialogue in train_dialogues}
    validation_ids = {dialogue["dialogue_id"] for dialogue in validation_dialogues}
    assert train_ids.isdisjoint(validation_ids)

    output_dir.mkdir(parents=True, exist_ok=True)
    save_examples(train, output_dir / "train.jsonl")
    save_examples(validation, output_dir / "validation.jsonl")
    report = {
        "source": "Team-ACE/ToolACE",
        "source_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "source_dialogues": len(rows),
        "seed": seed,
        "validation_fraction": 0.1,
        "train_dialogue_ids": sorted(train_ids),
        "validation_dialogue_ids": sorted(validation_ids),
        "train_examples": len(train),
        "validation_examples": len(validation),
        "excluded_dialogues": errors,
    }
    (output_dir / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Подготовить ToolACE для RL")
    parser.add_argument("--input", default="data/raw/data.json")
    parser.add_argument("--output", default="data/prepared")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = prepare_data(args.input, args.output, args.limit, args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))


