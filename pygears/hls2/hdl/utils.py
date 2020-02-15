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


