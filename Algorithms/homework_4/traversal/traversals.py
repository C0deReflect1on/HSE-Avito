from bst import Node, BinarySearchTree
from typing import Optional
from collections import deque

def view(bst: BinarySearchTree):
    if bst is None:
        return
    queue = deque([bst.root])
    while queue:
        node = queue.popleft()
        yield node.value
        if node.left:
            queue.append(node.left)
        if node.right:
            queue.append(node.right)

def pre_order(bst: BinarySearchTree):
    def _pre_order(n: Optional[Node]):
        if n is not None:
            yield n.value
            yield from _pre_order(n.left)
            yield from _pre_order(n.right)
    yield from _pre_order(bst.root)

def post_order(bst: BinarySearchTree):
    def _post_order(n: Optional[Node]):
        if n is not None:
            yield from _post_order(n.left)
            yield from _post_order(n.right)
            yield n.value
    yield from _post_order(bst.root)

def in_order(bst: BinarySearchTree):
    def _in_order(n: Optional[Node]):
        if n is not None:
            yield from _in_order(n.left)
            yield n.value
            yield from _in_order(n.right)
    yield from _in_order(bst.root)

def reverse_pre_order(bst: BinarySearchTree):
    def _reverse_pre_order(n: Optional[Node]):
        if n is not None:
            yield n.value
            yield from _reverse_pre_order(n.right)
            yield from _reverse_pre_order(n.left)
    yield from _reverse_pre_order(bst.root)

def reverse_post_order(bst: BinarySearchTree):
    def _reverse_post_order(n: Optional[Node]):
        if n is not None:
            yield from _reverse_post_order(n.right)
            yield from _reverse_post_order(n.left)
            yield n.value
    yield from _reverse_post_order(bst.root)

def reverse_in_order(bst: BinarySearchTree):
    def _reverse_in_order(n: Optional[Node]):
        if n is not None:
            yield from _reverse_in_order(n.right)
            yield n.value
            yield from _reverse_in_order(n.left) 
    yield from _reverse_in_order(bst.root)

bst_Tree = BinarySearchTree()
[15, 10, 20, 8, 12, 17, 25, 6, 9]
bst_Tree.insert(15)
bst_Tree.insert(10)
bst_Tree.insert(20)
bst_Tree.insert(8)
bst_Tree.insert(12)
bst_Tree.insert(17)
bst_Tree.insert(25)
bst_Tree.insert(6)
bst_Tree.insert(9)

print(list(view(bst_Tree)))
print(list(pre_order(bst_Tree)))
print(list(post_order(bst_Tree)))
print(list(in_order(bst_Tree)))
print(list(reverse_pre_order(bst_Tree)))
print(list(reverse_post_order(bst_Tree)))
print(list(reverse_in_order(bst_Tree)))