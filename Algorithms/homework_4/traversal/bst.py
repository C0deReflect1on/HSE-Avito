class Node:
    def __init__(self, value):
        self.value = value
        self.right = None
        self.left = None

class BinarySearchTree:
    def __init__(self):
        self.root = None

    def insert(self, value):
        if self.root is None:
            self.root = Node(value)
        else:
            current = self.root
            while True:
                if current.value > value:
                    if current.left is None:
                        current.left = Node(value)
                        break
                    current = current.left       
                else:
                    if current.right is None:
                        current.right = Node(value)
                        break
                    current = current.right
