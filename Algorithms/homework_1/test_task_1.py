import pytest
from task_1 import main


@pytest.mark.parametrize("num,expected", [
    (0, True),
    (1, True),
    (123, False),
    (121, True),
    (1221, True),
    (1223, False),
    (9, True),
    (10, False),
    (9999, True),
    (98, False),
])
def test_main(monkeypatch, num, expected):
    # Подменяем input() так, чтобы он "возвращал" нужное число
    monkeypatch.setattr("builtins.input", lambda: str(num))
    assert main() == expected
