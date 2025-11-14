import pytest
import random
import time
from copy import copy
from makeheap_n import makeheap_n
from makeheap_n_log_n import makeheap_n_log_n

# Проверка корректности кучи

def is_min_heap(a):
    n = len(a)
    for i in range(n):
        left = 2*i + 1
        right = 2*i + 2
        if left < n and a[i] > a[left]:
            return False
        if right < n and a[i] > a[right]:
            return False
    return True

@pytest.mark.parametrize("arr", [
    [],
    [5],
    [1,2,3,4,5],
    [5,4,3,2,1],
    [9,8,3,12,1,0],
    [10, -1, 7, -5, 2, 2, 999, 4],
])
def test_basic_makeheap_n_log_n(arr):
    h = makeheap_n_log_n(arr)
    assert is_min_heap(h)


@pytest.mark.parametrize("arr", [
    [],
    [5],
    [1,2,3,4,5],
    [5,4,3,2,1],
    [9,8,3,12,1,0],
    [10, -1, 7, -5, 2, 2, 999, 4],
])
def test_basic_makeheap_n(arr):
    h = makeheap_n(arr)
    assert is_min_heap(h)


def test_random_small():
    for _ in range(50):
        arr = [random.randint(-1000,1000) for _ in range(40)]
        h1 = makeheap_n(arr)
        h2 = makeheap_n_log_n(arr)
        assert is_min_heap(h1)
        assert is_min_heap(h2)


def test_random_large():
    arr = [random.randint(-10**7, 10**7) for _ in range(5000)]
    h1 = makeheap_n(arr)
    h2 = makeheap_n_log_n(arr)
    assert is_min_heap(h1)
    assert is_min_heap(h2)


def test_benchmark():
    n = 100
    arr = [random.randint(0, 10_000) for _ in range(n)]

    t0 = time.time()
    makeheap_n_log_n(arr)
    t1 = time.time()

    t2 = time.time()
    makeheap_n(arr)
    t3 = time.time()

    print("\nO(n log n):", t1 - t0)
    print("O(n)      :", t3 - t2)

    assert (t3 - t2) < (t1 - t0) # makeheap_n должен быть быстрее
