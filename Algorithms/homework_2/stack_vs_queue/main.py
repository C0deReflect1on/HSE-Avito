class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class Stack:
    '''LIFO'''
    def __init__(self):
        self.head = None
        self._size = 0

    def push(self, value):
        node = Node(value)
        node.next = self.head
        self.head = node # добавляем всегда перед головой (делаем новую)
        self._size += 1

    def pop(self):
        if self.head is None:
            raise IndexError("Stack is Empty")
        node = self.head
        self.head = node.next
        self._size -= 1
        return node.value

    def __len__(self):
        return self._size


class Queue:
    '''FIFO with dummy'''
    def __init__(self):
        self.dummy = Node(0)
        self.head = self.dummy
        self.tail = self.dummy
        self._size = 0

    def enqueue(self, value):
        node = Node(value)
        self.tail.next = node
        self.tail = node
        self._size += 1

    def dequeue(self):
        if self.dummy.next is None:
            raise IndexError("Queue is empty")
        node = self.dummy.next
        self.dummy.next = node.next
        if self.tail == node:
            # если удаляем последний элемент, tail возвращаем на dummy
            self.tail = self.dummy
        self._size -= 1
        return node.value

    def __len__(self):
        return self._size

    def view(self): # вспомогательная функция для отладки
        out = []
        cur = self.dummy.next
        while cur:
            out.append(cur.value)
            cur = cur.next
        return out
