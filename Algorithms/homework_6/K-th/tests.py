from main import quick_select


def test_quick_select_basic():
    arr = [3, 1, 5, 2, 4]
    # 1-й по убыванию = 5
    assert quick_select(arr, 1) == 5
    # 3-й по убыванию = 3
    assert quick_select(arr, 3) == 3
    # 5-й по убыванию = 1
    assert quick_select(arr, 5) == 1


def test_quick_select_duplicates():
    arr = [4, 1, 4, 2, 4, 3]
    # 2-й по убыванию = 4
    assert quick_select(arr, 2) == 4
    # 5-й по убыванию = 2
    assert quick_select(arr, 5) == 2


def test_quick_select_sorted_input():
    arr = [10, 9, 8, 7, 6]
    assert quick_select(arr, 1) == 10
    assert quick_select(arr, 5) == 6


def test_quick_select_single_element():
    arr = [42]
    assert quick_select(arr, 1) == 42


def test_quick_select_all_equal():
    arr = [7, 7, 7, 7, 7]
    for k in range(1, len(arr) + 1):
        assert quick_select(arr, k) == 7
