import pytest
from main import main

@pytest.mark.parametrize("arr_input,k_input,expected", [
    ("1 2 3 4 5", "5", (1, 2)),
    ("10 15 3 7", "17", (0, 3)),
    ("1 2 3", "10", -1),
    ("5 5", "10", (0, 1)),
    ("-1 -2 3 7", "6", (0, 3)),
])
def test_main(monkeypatch, arr_input, k_input, expected):
    inputs = iter([arr_input, k_input])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))
    result = main()
    assert result == expected