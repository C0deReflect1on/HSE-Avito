import pytest
from main import main

@pytest.mark.parametrize("pushed,poped,expected", [
    (["1","2","3"], ["2","1","3"], True),
    (["1","2","3"], ["3","2","1"], True),
    (["1","2","3"], ["3","1","2"], False),
    (["1"], ["1"], True),
    (["1","2"], ["2","1"], True),
    (["1","2"], ["1","2"], True),
    (["1","2","3","4"], ["4","3","2","1"], True),
    (["1","2","3","4"], ["2","1","4","3"], True),
])
def test_main(monkeypatch, pushed, poped, expected):
    inputs = iter([
        " ".join(pushed), 
        " ".join(poped)
    ])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))
    assert main() == expected
