import heapq
import random
import pytest

from manual_heap import kth_largest_custom
from heapq_ import kth_largest_heapq

@pytest.mark.parametrize("arr,k,expected", [
    ([1], 1, 1),
    ([5,4,3,2,1], 1, 5),
    ([5,4,3,2,1], 5, 1),
    ([3,1,2], 2, 2),
    ([10, -1, 0, 99], 1, 99),
    ([10, -1, 0, 99], 4, -1),
])
def test_basic_cases(arr, k, expected):
    assert kth_largest_custom(arr, k) == expected
    assert kth_largest_heapq(arr, k) == expected


@pytest.mark.parametrize("arr,k", [
    ([9,8,7,1,2,3], 3),
    ([100,50,20,10,5], 2),
    ([1,2,3,4,5], 4),
])
def test_small_sets(arr, k):
    expected = sorted(arr)[-k]
    assert kth_largest_custom(arr, k) == expected
    assert kth_largest_heapq(arr, k) == expected


def test_random_small():
    for _ in range(200):
        arr = [random.randint(-500,500) for _ in range(20)]
        k = random.randint(1, len(arr))
        expected = sorted(arr)[-k]
        assert kth_largest_custom(arr, k) == expected
        assert kth_largest_heapq(arr, k) == expected


def test_random_medium():
    for _ in range(20):
        arr = [random.randint(-10**6, 10**6) for _ in range(2000)]
        k = random.randint(1, len(arr))
        expected = sorted(arr)[-k]
        assert kth_largest_custom(arr, k) == expected
        assert kth_largest_heapq(arr, k) == expected


def test_same_output_both_methods():
    for _ in range(50):
        arr = [random.randint(-1000,1000) for _ in range(100)]
        k = random.randint(1, len(arr))
        assert (
            kth_largest_custom(arr, k)
            == kth_largest_heapq(arr, k)
        )
