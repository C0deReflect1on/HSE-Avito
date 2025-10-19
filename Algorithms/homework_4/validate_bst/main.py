class Node:
    def __init__(self, value):
        self.value = value
        self.right = None
        self.left = None


def validate_bst(root: Node):
    left = float('-inf')
    right = float('+inf')
    def _validate(node, left, right):
        if node is None:
            return True
        if not (left <= node.value < right): # дубликаты идут на право
            return False
        return (
            _validate(node.left, left, node.value) and 
            _validate(node.right, node.value, right)
        )
    return _validate(root, left, right)
