import pytest
from main import Stack, Queue


class TestStack:
    def test_push_pop_len(self):
        st = Stack()
        assert len(st) == 0

        st.push(1)
        st.push(2)
        st.push(3)
        assert len(st) == 3

        assert st.pop() == 3
        assert st.pop() == 2
        assert st.pop() == 1
        assert len(st) == 0

    def test_pop_empty_raises(self):
        st = Stack()
        with pytest.raises(IndexError):
            st.pop()

    def test_order_LIFO(self):
        st = Stack()
        for i in range(5):
            st.push(i)
        result = [st.pop() for _ in range(5)]
        assert result == [4, 3, 2, 1, 0]


class TestQueue:
    def test_enqueue_dequeue_len_view(self):
        q = Queue()
        assert len(q) == 0
        assert q.view() == []

        q.enqueue(1)
        q.enqueue(2)
        q.enqueue(3)
        assert len(q) == 3
        assert q.view() == [1, 2, 3]

        assert q.dequeue() == 1
        assert q.dequeue() == 2
        assert q.dequeue() == 3
        assert len(q) == 0
        assert q.view() == []

    def test_dequeue_empty_raises(self):
        q = Queue()
        with pytest.raises(IndexError):
            q.dequeue()

    def test_tail_resets_after_dequeue_last(self):
        q = Queue()
        q.enqueue(10)
        assert q.tail.value == 10
        q.dequeue()
        assert q.tail == q.head

    def test_order_FIFO(self):
        q = Queue()
        for i in range(5):
            q.enqueue(i)
        result = [q.dequeue() for _ in range(5)]
        assert result == [0, 1, 2, 3, 4]
