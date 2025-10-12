import pytest
from main import main

@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("eat tea tan ate nat bat", [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]),
        ("", []),
        ("a", [["a"]]),
        ("abc bca cab bac", [["abc", "bca", "cab", "bac"]]),
        ("dog god odg dgo gda", [["dog", "god", "odg", "dgo"], ["gda"]]),
    ],
)
def test_main(monkeypatch, input_str, expected):
    monkeypatch.setattr("builtins.input", lambda: input_str)
    result = main()
    assert all(sorted(group) in [sorted(e) for e in expected] for group in result)
    assert len(result) == len(expected)
