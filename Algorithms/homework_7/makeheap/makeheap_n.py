from copy import copy


def sift_down(heap, i):
    while 2*i+1 < len(heap):
        right_kid = None
        left_kid = None
        t_idx = None
        if 2*i+2 < len(heap):
            right_kid = heap[2*i+2]
            left_kid = heap[2*i+1]
            if right_kid < left_kid:
                t_idx = 2*i + 2
            else:
                t_idx = 2*i + 1
        else:
            t_idx = 2*i+1       
        if heap[i] >= heap[t_idx]:
            heap[i], heap[t_idx] = heap[t_idx], heap[i]
            i = t_idx # после замены надо у него проверять теперь
        else:
            break

def makeheap_n(arr):
    heap = copy(arr)
    n = len(heap)
    
    for i in range((n - 2) // 2, -1, -1):
        sift_down(heap, i)
    return heap
