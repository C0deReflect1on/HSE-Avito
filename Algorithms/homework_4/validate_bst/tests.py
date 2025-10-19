import pytest
from main import Node, validate_bst

def make_valid_bst():
    #      10
    #     /  \
    #    5   15
    #       /  \
    #      12  20
    root = Node(10)
    root.left = Node(5)
    root.right = Node(15)
    root.right.left = Node(12)
    root.right.right = Node(20)
    return root

def make_invalid_bst_left_violation():
    #      10
    #     /
    #    15 ошибка: левый > родителя
    root = Node(10)
    root.left = Node(15)
    return root

def make_duplicate_right_ok():
    #      10
    #        \
    #         10 дубликат вправо допустим
    root = Node(10)
    root.right = Node(10)
    return root

def make_duplicate_left_fail():
    #      10
    #     /
    #    10 дубликат влево недопустим
    root = Node(10)
    root.left = Node(10)
    return root

def make_single_node():
    return Node(5)


def test_valid_bst():
    assert validate_bst(make_valid_bst()) is True

def test_invalid_bst_left_violation():
    assert validate_bst(make_invalid_bst_left_violation()) is False

def test_duplicate_right_ok():
    assert validate_bst(make_duplicate_right_ok()) is True

def test_duplicate_left_fail():
    assert validate_bst(make_duplicate_left_fail()) is False

def test_single_node_bst():
    assert validate_bst(make_single_node()) is True
