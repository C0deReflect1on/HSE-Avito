import pytest
from bst import BinarySearchTree
from traversals import pre_order, post_order, in_order, \
                reverse_pre_order, reverse_post_order, reverse_in_order


def build_tree(values):
    """Helper: создаёт BST и вставляет значения в том порядке, который указан."""
    t = BinarySearchTree()
    for v in values:
        t.insert(v)
    return t


def test_empty_tree_traversals_are_empty():
    t = BinarySearchTree()
    assert list(pre_order(t)) == []
    assert list(post_order(t)) == []
    assert list(in_order(t)) == []
    assert list(reverse_pre_order(t)) == []
    assert list(reverse_post_order(t)) == []
    assert list(reverse_in_order(t)) == []


def test_single_node_tree():
    t = build_tree([42])
    expected = [42]
    assert list(pre_order(t)) == expected
    assert list(post_order(t)) == expected
    assert list(in_order(t)) == expected
    assert list(reverse_pre_order(t)) == expected
    assert list(reverse_post_order(t)) == expected
    assert list(reverse_in_order(t)) == expected


def test_left_skewed_tree():
    # вставляем по убыванию => все идут в left
    values = [5, 4, 3, 2]
    t = build_tree(values)

    assert list(pre_order(t)) == [5, 4, 3, 2]
    assert list(post_order(t)) == [2, 3, 4, 5]
    assert list(in_order(t)) == sorted(values)
    assert list(reverse_in_order(t)) == sorted(values, reverse=True)
    # reverse_pre_order on left-skewed == pre_order (нет правых детей)
    assert list(reverse_pre_order(t)) == [5, 4, 3, 2]
    # reverse_post_order on left-skewed == post_order
    assert list(reverse_post_order(t)) == [2, 3, 4, 5]


def test_right_skewed_tree():
    # вставляем по возрастанию => все идут в right
    values = [2, 3, 4, 5]
    t = build_tree(values)

    assert list(pre_order(t)) == [2, 3, 4, 5]
    assert list(post_order(t)) == [5, 4, 3, 2]
    assert list(in_order(t)) == sorted(values)
    assert list(reverse_in_order(t)) == sorted(values, reverse=True)
    # reverse_pre_order on right-skewed == pre_order (все в правом поддереве)
    assert list(reverse_pre_order(t)) == [2, 3, 4, 5]
    # reverse_post_order equals post_order reversed? here it's [5,4,3,2]
    assert list(reverse_post_order(t)) == [5, 4, 3, 2]


def test_balanced_like_tree():
    # пример дерева с левым потомком у 8 (6 и 9) и обычными правыми/левыми
    values = [15, 10, 20, 8, 12, 17, 25, 6, 9]
    t = build_tree(values)

    # ожидаемые последовательности
    expected_pre = [15, 10, 8, 6, 9, 12, 20, 17, 25]
    expected_post = [6, 9, 8, 12, 10, 17, 25, 20, 15]
    expected_in = sorted(values)
    expected_rev_in = sorted(values, reverse=True)
    expected_rev_pre = [15, 20, 25, 17, 10, 12, 8, 9, 6]
    expected_rev_post = [25, 17, 20, 12, 9, 6, 8, 10, 15]

    assert list(pre_order(t)) == expected_pre
    assert list(post_order(t)) == expected_post
    assert list(in_order(t)) == expected_in
    assert list(reverse_in_order(t)) == expected_rev_in
    assert list(reverse_pre_order(t)) == expected_rev_pre
    assert list(reverse_post_order(t)) == expected_rev_post


def test_in_order_sorted_property_for_random_sequences():
    # in-order BFS property: для BST in_order == sorted(inserted_values)
    sequences = [
        [10, 5, 15, 3, 7, 12, 20],
        [1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1],
        [10, 9, 11, 9, 12]  # содержит дубликат 9
    ]
    for seq in sequences:
        t = build_tree(seq)
        assert list(in_order(t)) == sorted(seq)
