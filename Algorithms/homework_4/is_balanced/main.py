class Node:
    def __init__(self, value):
        self.value = value
        self.right = None
        self.left = None


def is_balanced(root: Node):
    def _get_depth(node):
        l = 0
        if node.left is not None:
            l = _get_depth(node.left)
        r = 0
        if node.right is not None:
            r = _get_depth(node.right)
        if not(-1 <= r - l <= 1):
            return False
        if l is False or r is False:
            return False
        return max(l,r) + 1
    if root is None:
        return True
    return _get_depth(root) is not False
