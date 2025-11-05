import random
from main import merge_sort_iterative, quick_sort_iterative

def test_merge_sort_correctness():
    arr = [5, 3, 8, 1, 2]
    sorted_arr = merge_sort_iterative(arr)
    assert sorted_arr == sorted(arr)

def test_quick_sort_correctness():
    arr = [9, 4, 6, 2, 7, 1]
    sorted_arr = quick_sort_iterative(arr)
    assert sorted_arr == sorted(arr)

def test_large_random_arrays():
    arr = [random.randint(0, 10000) for _ in range(1000)]
    assert merge_sort_iterative(arr) == sorted(arr)
    assert quick_sort_iterative(arr) == sorted(arr)

def test_speed_measurement():
    # Здесь просто демонстрация — время выведется при вызове
    # По реализации выборса pivot, нет худших/лучших случаев, всегда O(nlog_2(n))
    arr = [random.randint(0, 10000) for _ in range(5000)]
    print("test speedap")
    merge_sort_iterative(arr)
    quick_sort_iterative(arr)
