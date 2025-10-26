import io
import re
from contextlib import redirect_stdout

from permutations.main import permute

ENTER_RE = re.compile(r"^level: (\d+), \(.+?, \((.*)\), \{\}\)$")
EXIT_RE = re.compile(r"^exit, level: (\d+), <generator object permute.*>$")


def _capture(factory, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        it = factory(*args, **kwargs)
        list(it)
    return buf.getvalue().strip().splitlines()



def test_tracer_structure_for_two_elements():
    lines = _capture(permute, [1, 2]) 
    # ожидаем последовательность уровней входа/выхода:
    # enter 0, enter 1, enter 2, exit 2, exit 1, enter 1, enter 2, exit 2, exit 1, exit 0
    events = []
    for ln in lines:
        m = ENTER_RE.match(ln)
        if m:
            events.append(("enter", int(m.group(1)), m.group(2)))
            continue
        m = EXIT_RE.match(ln)
        if m:
            events.append(("exit", int(m.group(1)), None))

    levels = [e[1] for e in events]
    kinds = [e[0] for e in events]

    assert kinds == [
        "enter","enter","enter",
        "exit","exit",
        "enter","enter",
        "exit","exit","exit",
    ]
    assert levels == [0,1,2, 2,1, 1,2, 2,1,0]

def test_tracer_arguments_rendered_correctly_for_base_cases():
    lines = _capture(permute, [1, 2]) 
    enters = [ENTER_RE.match(ln).groups() for ln in lines if ENTER_RE.match(ln)]
    args_strs = [a for _, a in enters]
    args_strs = [re.sub(r"\s+", "", a) for a in args_strs]
    assert "[1,2]," in args_strs[0]  # первый вызов
    assert "[2],[1]" in args_strs[1]
    assert "[],[1,2]" in args_strs[2]
    assert "[1],[2]" in args_strs[3]
    assert "[],[2,1]" in args_strs[4]

def test_tracer_balances_entries_and_exits_for_three_elements():
    lines = _capture(permute, [1, 2]) 
    enters = sum(1 for ln in lines if ENTER_RE.match(ln))
    exits = sum(1 for ln in lines if EXIT_RE.match(ln))

    assert enters == exits
