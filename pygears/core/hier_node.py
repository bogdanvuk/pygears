class HierVisitorBase:
    def visit(self, node):
        import inspect
        for base_class in reversed(inspect.getmro(node.__class__)):
            if hasattr(self, base_class.__name__):
                getattr(self, base_class.__name__)(node)

    def HierNode(self, node):
        if hasattr(node, "child"):
            # Iterate over a copy in case visiting removes or adds children
            # from the parent
            for c in list(node.child):
                self.visit(c)


class HierNode:
    def __init__(self, parent=None):
        self.child = []
        self.parent = None
        if parent:
            parent.add_child(self)

    def add_child(self, module):
        self.child.append(module)
        module.parent = self

    def remove(self):
        if self.parent:
            self.parent.child.remove(self)
