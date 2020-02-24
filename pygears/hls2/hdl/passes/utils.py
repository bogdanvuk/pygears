import inspect

from .. import pydl
from pygears.typing import Bool
from .. import nodes

def add_to_list(orig_list, extension):
    if extension:
        orig_list.extend(
            extension if isinstance(extension, list) else [extension])


res_true = pydl.ResExpr(Bool(True))
res_false = pydl.ResExpr(Bool(False))

class Scope:
    def __init__(self, parent=None):
        self.parent = None
        self.child = None
        self.items = {}

    def subscope(self):
        if self.child is None:
            self.child = Scope(parent=self)
            self.child.parent = self
            return self.child

        return self.child.subscope()

    def upscope(self):
        s = self.cur_subscope
        s.parent.child = None
        s.parent = None

    @property
    def cur_subscope(self):
        if self.child is None:
            return self

        return self.child.cur_subscope

    @property
    def top_scope(self):
        if self.parent is not None:
            return self.parent.top_scope

        return self

    def clear(self):
        self.child.clear()
        self.child = None
        self.items.clear()

    def __getitem__(self, key):
        if self.child:
            try:
                return self.child[key]
            except KeyError:
                pass

        return self.items[key]

    def __delitem__(self, key):
        if self.child:
            try:
                del self.child[key]
            except KeyError:
                pass

        del self.items[key]

    def __contains__(self, key):
        if self.child and key in self.child:
            return True

        return key in self.items

    def __setitem__(self, key, val):
        if self.child:
            self.child[key] = val
            return

        self.items[key] = val

    def __iter__(self):
        scope = self.cur_subscope
        keys = set()
        while True:
            for key in scope.items:
                if key not in keys:
                    yield key
                    keys.add(key)

            if scope.parent is None:
                return

            scope = scope.parent


class HDLVisitor:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def generic_visit(self, node):
        return node

__all__ = ['Scope', 'HDLVisitor', 'res_true', 'res_false', 'add_to_list', 'nodes']
