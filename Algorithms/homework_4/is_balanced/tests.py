import pytest
from main import Node, is_balanced


def make_empty():
    return None

def make_root_only():
    return Node(10)

def make_valid_symmetric():
    #       10
    #     /    \
    #    5      15
    #   / \    /  \
    #  3   7  12  18
    root = Node(10)
    root.left = Node(5)
    root.right = Node(15)
    root.left.left = Node(3)
    root.left.right = Node(7)
    root.right.left = Node(12)
    root.right.right = Node(18)
    return root

def make_three_right_chain_invalid():
    # 10 -> 15 -> 20 -> (no lefts)  (chain of length 3 to the right)
    # root.left height = 0, root.right height = 2 => abs = 2 -> not balanced
    root = Node(10)
    root.right = Node(15)
    root.right.right = Node(20)
    return root

def make_three_left_chain_invalid():
    # mirror: chain left-left-left
    root = Node(10)
    root.left = Node(5)
    root.left.left = Node(2)
    return root

def make_two_right_valid():
    # 10 -> 15 (single right child) balanced
    root = Node(10)
    root.right = Node(15)
    return root

def make_two_left_valid():
    # 10 -> 5 (single left child) balanced
    root = Node(10)
    root.left = Node(5)
    return root

def make_left_error_deep():
    # first level looks ok, but deep left subtree is unbalanced
    # root:10
    # left:5 -> left:3 -> left:1  (height 3)
    # right:12 (height 1)
    # root: left height 3, right height 1 -> abs = 2 -> not balanced
    root = Node(10)
    root.left = Node(5)
    root.right = Node(12)
    root.left.left = Node(3)
    root.left.left.left = Node(1)
    return root

def make_right_error_deep():
    # symmetric to make_left_error_deep
    root = Node(10)
    root.right = Node(15)
    root.left = Node(8)
    root.right.right = Node(20)
    root.right.right.right = Node(25)
    return root

def make_both_children_unbalanced():
    # Both left and right subtrees individually unbalanced (so whole tree is unbalanced),
    # even if their heights happen to be similar.
    # left subtree: 7 -> 6 -> 5 -> 4  (unbalanced inside)
    # right subtree: 17 -> 18 -> 19 -> 20 (also unbalanced inside)
    root = Node(10)
    # left internally unbalanced
    root.left = Node(7)
    root.left.left = Node(6)
    root.left.right = Node(6)
    root.left.left.left = Node(5)
    root.left.left.left.left = Node(4)
    # right internally unbalanced
    root.right = Node(17)
    root.right.right = Node(18)
    root.right.left = Node(18)
    root.right.right.right = Node(19)
    root.right.right.right.right = Node(20)
    return root


def test_empty_tree_is_balanced():
    assert is_balanced(make_empty()) is True

def test_root_only_is_balanced():
    assert is_balanced(make_root_only()) is True

def test_valid_symmetric_is_balanced():
    assert is_balanced(make_valid_symmetric()) is True

def test_two_right_valid_is_balanced():
    assert is_balanced(make_two_right_valid()) is True

def test_two_left_valid_is_balanced():
    assert is_balanced(make_two_left_valid()) is True

def test_three_right_chain_is_not_balanced():
    assert is_balanced(make_three_right_chain_invalid()) is False

def test_three_left_chain_is_not_balanced():
    assert is_balanced(make_three_left_chain_invalid()) is False

def test_left_deep_error_bubbles_up():
    assert is_balanced(make_left_error_deep()) is False

def test_right_deep_error_bubbles_up():
    assert is_balanced(make_right_error_deep()) is False

def test_both_children_unbalanced():
    assert is_balanced(make_both_children_unbalanced()) is False
