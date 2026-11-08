"""Parse Qwen output and score tool calls without executing tools."""

import json
import re
from collections import Counter

def parse_qwen_calls(text, tools):
    if not text.strip():
        raise ValueError("Пустой ответ")

    schemas = {
        tool["function"]["name"]: tool["function"]["parameters"]
        for tool in tools
    }

    # shortcut: literal closing tags in values need a native parser if they occur.
    call_pattern = r"<tool_call>(.*?)</tool_call>"
    remaining = re.sub(call_pattern, "", text, flags=re.S)

    markup = (
        "<tool", "</tool",
        "<function", "</function",
        "<parameter", "</parameter",
    )
    if any(tag in remaining for tag in markup):
        raise ValueError("Незакрытая или лишняя разметка вызова")

    calls = []

    for block in re.findall(call_pattern, text, flags=re.S):
        function = re.fullmatch(
            r"\s*<function=([^>]+)>(.*?)</function>\s*",
            block,
            flags=re.S,
        )
        if function is None:
            raise ValueError("Некорректная разметка функции")

        name = function.group(1).strip()
        if name not in schemas:
            raise ValueError(f"Неизвестная функция: {name}")

        schema = schemas[name]
        parameters = function.group(2)
        parameter_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"

        if re.sub(parameter_pattern, "", parameters, flags=re.S).strip():
            raise ValueError("Некорректная разметка аргументов")

        arguments = {}

        for key, raw_value in re.findall(
            parameter_pattern, parameters, flags=re.S
        ):
            key = key.strip()

            if key in arguments or key not in schema.get("properties", {}):
                raise ValueError(f"Повторный или неизвестный аргумент: {key}")

            value = raw_value.strip()
            parameter_type = schema["properties"][key].get("type", "string")

            if parameter_type == "string":
                arguments[key] = value
            else:
                arguments[key] = json.loads(value)

        missing = set(schema.get("required") or []) - arguments.keys()
        if missing:
            raise ValueError(
                f"Не переданы обязательные аргументы: {sorted(missing)}"
            )

        calls.append({
            "name": name,
            "arguments": arguments,
        })

    return calls


def canonical_calls(calls):
    serialized = []
    for call in calls:
        serialized.append(json.dumps(call, sort_keys=True, ensure_ascii=False))
    return sorted(serialized)


def score_response(response, answer, tools):
    try:
        predicted = parse_qwen_calls(response, tools)
    except ValueError:
        return {"exact": 0.0, "functions": 0.0, "format": 0.0}

    expected = []
    for call in answer.get("tool_calls", []):
        expected.append(call["function"])

    exact = float(canonical_calls(expected) == canonical_calls(predicted))
    expected_names = Counter(call["name"] for call in expected)
    predicted_names = Counter(call["name"] for call in predicted)
    matched = sum((expected_names & predicted_names).values())
    total = len(expected) + len(predicted)
    functions = 2 * matched / total if total else 1.0
    return {"exact": exact, "functions": functions, "format": 1.0}


def reward(response, answer, tools):
    return int(score_response(response, answer, tools)["exact"])


def function_reward(response, answer, tools):
    return score_response(response, answer, tools)["functions"]


def format_reward(response, answer, tools):
    return score_response(response, answer, tools)["format"]


def format_reference(answer):
    """Create a canned Qwen response for local checks, not training generations."""
    if not answer.get("tool_calls"):
        return answer["content"]

    parts = []
    for tool_call in answer["tool_calls"]:
        function = tool_call["function"]
        parts.append("<tool_call>")
        parts.append(f'<function={function["name"]}>')
        for name, value in function["arguments"].items():
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            parts.extend([f"<parameter={name}>", value, "</parameter>"])
        parts.extend(["</function>", "</tool_call>"])
    return "\n".join(parts)


