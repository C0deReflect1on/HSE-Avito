import time
from functools import wraps


def timer(recursive=False):
    def decorator(func):
        depth = 0
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal depth
            top_call = depth == 0
            depth += 1
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            if not recursive or top_call:
                print(f"Время выполнения {func.__name__}: {end - start:.4f} сек")
            depth -= 1
            return result
        return wrapper
    return decorator


def merge_sorted(arr1: list[int], arr2: list[int]) -> list[int]:
    sorted_arr = []
    i,j = 0, 0
    while i < len(arr1) and j < len(arr2):
        if arr1[i] <= arr2[j]:
            sorted_arr.append(arr1[i])
            i += 1
        else:
            sorted_arr.append(arr2[j])
            j += 1
    if i == len(arr1):
        sorted_arr.extend(arr2[j:])
    else:
        sorted_arr.extend(arr1[i:])

    return sorted_arr


@timer(recursive=True)
def merge_sort_recursive(array: list[int]):
    if len(array) == 1:
        return array
    else:
        mid = len(array)//2
        arr_l = array[:mid]
        arr_r = array[mid:]
        return merge_sorted(merge_sort_recursive(arr_l), merge_sort_recursive(arr_r))


@timer(recursive=True)
def quick_sort_recursive(array: list[int]):
    if len(array) <= 1:
        return array
    else:
        pivot_idx = len(array)//2
        arr_l = []
        arr_r = []
        for i in range(len(array)):
            if i == pivot_idx:
                continue
            if array[i] < array[pivot_idx]:
                arr_l.append(array[i])
            else:
                arr_r.append(array[i])
        return quick_sort_recursive(arr_l) + [array[pivot_idx]] + quick_sort_recursive(arr_r)

