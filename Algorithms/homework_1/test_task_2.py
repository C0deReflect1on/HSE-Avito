import pytest
from task_2 import main


@pytest.mark.parametrize("nums,expected", [
   ([2, 4, 6], 12),
   ([2, 4, 6, 1], 12),
   ([2, 4, 6, 9, 1], 22),
   ([1, 2, 3, 4, 5, 6], 20),
   ([1, 3, 5], 8),
   ([1, 3], 4),
   ([1], 0),
   ([2], 2)
])
def test_main(monkeypatch, nums, expected):
    monkeypatch.setattr("builtins.input", lambda: " ".join([str(s) for s in nums]))
    assert main() == expected
