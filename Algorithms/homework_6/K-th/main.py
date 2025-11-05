def quick_select(arr, k):
    start = 0
    i = 0
    k = len(arr)-k+1
    ans = None
    while True:
        pivot_idx = len(arr)//2
        left = [elem for elem in arr if elem < arr[pivot_idx]]
        right = [elem for elem in arr if elem > arr[pivot_idx]]
        pivots = [elem for elem in arr if elem == arr[pivot_idx]]
        pivot_idx_new = start + len(left) + 1
        if pivot_idx_new == k:
            ans = pivots[0]
            break
        if pivot_idx_new > k:
            arr = left
        else:
            if k <= start+len(left)+len(pivots):
                ans = pivots[0]
                break
            else:
                arr = pivots + right
                start += len(left)
                

    return ans
