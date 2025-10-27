from typing import Optional


class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
        self.height = 1
    
    @staticmethod
    def get_height(node):
        return node.height if node else 0
    
    def get_balance(self):
        return self.get_height(self.left) - self.get_height(self.right)
    
class AVLTree:
    def __init__(self):
        self.root = None
    
    def _rotate_right(self, node: Node):
        # node -> l1 -> l1r? | l1l
        l1 = node.left
        l1r = l1.right
        l1.right = node
        node.left = l1r
        self._update(node)
        self._update(l1)
        return l1 # new local root
    
    def _rotate_left(self, node: Node):
        # node -> r1 -> r1l? | r1r
        r1 = node.right
        r1l = r1.left
        r1.left = node
        node.right = r1l
        self._update(node)
        self._update(r1)
        return r1 # new local root

    
    @staticmethod
    def get_height(node: Optional[Node]):
        return node.height if node else 0

    def _update(self, node):
        node.height = 1 + max(Node.get_height(node.left), Node.get_height(node.right))

    def _insert(self, local_root, value):
        if local_root is None:
            return Node(value)
        
        if local_root.value > value:
            local_root.left = self._insert(local_root.left, value)
        elif local_root.value < value:
            local_root.right = self._insert(local_root.right, value)
        else:
            return local_root
        
        self._update(local_root)
        balance = local_root.get_balance()
        if balance > 1: ## LL, LR
            if local_root.left.value < value:
                local_root.left = self._rotate_left(local_root.left) # LR
            return self._rotate_right(local_root) #LL

        if balance < -1: ## RR, RL
            if value < local_root.right.value:
                local_root.right = self._rotate_right(local_root.right) # RL
            return self._rotate_left(local_root) ## RR

        return local_root

    def insert(self, value):
        self.root = self._insert(self.root, value)
