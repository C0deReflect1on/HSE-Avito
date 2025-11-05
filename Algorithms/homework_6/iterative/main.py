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


def merge_sort_iterative(array: list[int]) -> list[int]: # хотя можно и inplace сделать
    _arr = array.copy()
    width = 1
    while width < len(_arr):
        for i in range(0,len(_arr)-width, 2*width):
            _arr[i: i+2*width] = merge_sorted(_arr[i:i+width], _arr[i+width:i+2*width])
        width = width << 1
    return _arr


def quick_sort_iterative(array: list[int]) -> list[int]:
    array = array.copy()
    stack = [(0, len(array) - 1)]
    while stack:
        l, r = stack.pop()
        if l >= r:
            continue

        pivot_idx = (l + r) // 2
        pivot_val = array[pivot_idx]
        _l, _r = [], []

        for i in range(l, r + 1):
            if i == pivot_idx:
                continue
            if array[i] < pivot_val:
                _l.append(array[i])
            else:
                _r.append(array[i])

        array[l:r + 1] = _l + [pivot_val] + _r
        pivot_new = l + len(_l)

        stack.append((l, pivot_new - 1))
        stack.append((pivot_new + 1, r))

    return array