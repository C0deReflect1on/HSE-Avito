import pytest
from task_3 import main

@pytest.mark.parametrize("n,expected", [
    (-1, "exception"),
    (1, 0),
    (2, 1),
    (3, 2),
    (4, 2),
    (10, 4),
    (100, 25)
])
def test_main(monkeypatch, n, expected):
    monkeypatch.setattr("builtins.input", lambda: str(n))
    
    if expected == "exception":
        with pytest.raises(Exception, match="Wrong input, n shouldbe > 0"):
            main()
    else:
        assert main() == expected
