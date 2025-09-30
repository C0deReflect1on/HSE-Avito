import pytest
from no_dummy import main

@pytest.mark.parametrize("l1,l2,expected", [
    (["1","3","5"], ["2","4","6"], [1,2,3,4,5,6]),
    ([], ["1","2","3"], [1,2,3]),
    (["1","2","3"], [], [1,2,3]),
    ([], [], None),
    (["5"], ["3"], [3,5]),
])
def test_main(monkeypatch, l1, l2, expected):
    inputs = iter([
        " ".join(l1),
        " ".join(l2)
    ])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))
    
    merged = main()
    if merged is None:
        assert merged == expected
    else:
        assert merged.view() == expected
