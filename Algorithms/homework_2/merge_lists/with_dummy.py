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
    if not l:
        return None
    
    head = LinkedList(0)
    curr = head

    for elem in l:
        curr.next = LinkedList(elem)
        curr = curr.next # move current node
    return head.next


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

    merged_head = LinkedList(0)
    curr_merge = merged_head

    while linked_l1 or linked_l2:
        curr_merge, linked_l1, linked_l2 = make_1_merge(curr_merge, linked_l1, linked_l2)

    return merged_head.next

if __name__ == "__main__":
    main()
