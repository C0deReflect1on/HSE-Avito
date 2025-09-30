from typing import Optional


class LinkedList:
    def __init__(self, value: int):
        self.value = value
        self.next: Optional[LinkedList] = None
    
    def view(self):
        head = self
        l = []
        while head:
            l.append(head.value)
            head = head.next
        
        return l


def create_linkedlist(l: list[int]) -> LinkedList:
    linked_l = None
    curr = None
    if not l:
        return None
    
    linked_l = LinkedList(l[0])
    curr = linked_l

    for elem in l[1:]:
        curr.next = LinkedList(elem)
        curr = curr.next # move current node
    return linked_l


def make_1_merge(tail, l1, l2):
    if l1 and l2:
        if l1.value <= l2.value:
            tail.next, l1 = l1, l1.next
        else:
            tail.next, l2 = l2, l2.next
    elif l1:
        tail.next, l1 = l1, l1.next
    elif l2:
        tail.next, l2 = l2, l2.next
    else:
        return None, None, None
    
    return tail.next, l1, l2


def main():
    l1 = list(map(int, input().split()))
    l2 = list(map(int, input().split()))

    linked_l1 = create_linkedlist(l1)
    linked_l2 = create_linkedlist(l2)
    merged_linked_l = None
    if not linked_l1:
        return linked_l2
    if not linked_l2:
        return linked_l1

    if linked_l1.value <= linked_l2.value:
        merged_linked_l = linked_l1
        linked_l1 = linked_l1.next
    else:
        merged_linked_l = linked_l2
        linked_l2 = linked_l2.next
    curr_merge = merged_linked_l

    while linked_l1 or linked_l2:
        # no order is supported for linked_l1 and linked_l2 on each step they can swap
        curr_merge, linked_l1, linked_l2 = make_1_merge(curr_merge, linked_l1, linked_l2)

    return merged_linked_l

if __name__ == "__main__":
    main()
