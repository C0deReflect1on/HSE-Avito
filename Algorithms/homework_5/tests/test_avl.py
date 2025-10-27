import pytest
from avl import AVLTree, Node


def inorder(node):
    """Рекурсивный обход для проверки BST-свойства."""
    if not node:
        return []
    return inorder(node.left) + [node.value] + inorder(node.right)


def test_single_insert():
    tree = AVLTree()
    tree.insert(10)
    assert tree.root.value == 10
    assert tree.root.height == 1
    assert inorder(tree.root) == [10]


def test_two_inserts_no_rotation():
    tree = AVLTree()
    for v in (10, 8):
        tree.insert(v)
    assert inorder(tree.root) == [8, 10]
    assert tree.root.value == 10
    assert tree.root.left.value == 8


def test_rr_rotation():
    tree = AVLTree()
    for v in (10, 20, 30):  # RR
        tree.insert(v)
    assert inorder(tree.root) == [10, 20, 30]
    assert tree.root.value == 20  # балансировалось
    assert tree.root.left.value == 10
    assert tree.root.right.value == 30


def test_ll_rotation():
    tree = AVLTree()
    for v in (30, 20, 10):  # LL
        tree.insert(v)
    assert inorder(tree.root) == [10, 20, 30]
    assert tree.root.value == 20
    assert tree.root.left.value == 10
    assert tree.root.right.value == 30


def test_lr_rotation():
    tree = AVLTree()
    for v in (30, 10, 20):  # LR
        tree.insert(v)
    assert inorder(tree.root) == [10, 20, 30]
    assert tree.root.value == 20


def test_rl_rotation():
    tree = AVLTree()
    for v in (10, 30, 20):  # RL
        tree.insert(v)
    assert inorder(tree.root) == [10, 20, 30]
    assert tree.root.value == 20


def test_balanced_after_many_inserts():
    tree = AVLTree()
    values = [50, 20, 10, 40, 70, 60, 80, 25, 30]
    for v in values:
        tree.insert(v)

    result = inorder(tree.root)
    assert result == sorted(values)
    # Проверяем, что дерево сбалансировано
    def check_balance(node):
        if not node:
            return True
        b = node.get_balance()
        assert -1 <= b <= 1
        return check_balance(node.left) and check_balance(node.right)
    assert check_balance(tree.root)
