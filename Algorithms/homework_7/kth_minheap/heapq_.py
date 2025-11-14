import heapq

def kth_largest_heapq(arr, k):
    heap = []

    for x in arr:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:
            heapq.heapreplace(heap, x)

    return heap[0]
