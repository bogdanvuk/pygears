import string
from collections import Counter


class HierYielderBase:
    def visit(self, node):
        import inspect
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                if (yield from getattr(self, base_class.__name__)(node)):
                    return

    def HierNode(self, node):
        if hasattr(node, "child"):
            # Iterate over a copy in case visiting removes or adds children
            # from the parent
            for c in list(node.child):
                yield from self.visit(c)


class HierVisitorBase:
    def visit(self, node):
        import inspect
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                if getattr(self, base_class.__name__)(node):
                    return

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

    def clear(self):
        for c in self.child.copy():
            if hasattr(c, 'remove'):
                c.remove()

        self.child = []

    def remove(self):
        if self.parent:
            self.parent.child.remove(self)

    def root(self):
        node = self
        while node.parent is not None:
            node = node.parent

        return node


def find_unique_names(names):
    def get_stem(s):
        return s.rstrip(string.digits)

    stems = list(map(get_stem, names))

    names_cnt = Counter(names)
    stems_cnt = Counter(stems)

    def unique(s):
        return names_cnt[s] <= 1

    def unique_stem(s):
        return stems_cnt[s] <= 1

    indexes = {k: 0 for k in stems_cnt}
    for name, stem in zip(names, stems):
        new_name = name
        if not unique_stem(stem):
            while ((new_name == stem) or (not unique(new_name))):
                names_cnt[new_name] -= 1
                new_name = f'{stem}{indexes[stem]}'
                if new_name in names_cnt:
                    names_cnt[new_name] += 1
                else:
                    names_cnt[new_name] = 1
                indexes[stem] += 1

        if new_name != name:
            yield new_name
        else:
            yield None


class NamedHierNode(HierNode):
    def __init__(self, basename=None, parent=None):
        super().__init__(parent)
        if basename is not None:
            self.basename = basename
            if parent:
                parent.unique_rename()

    def unique_rename(self):
        child_names = [c.basename for c in self.child]
        for child, new_name in zip(self.child, find_unique_names(child_names)):
            if new_name:
                child.basename = new_name

    def __contains__(self, path):
        try:
            self[path]
            return True
        except KeyError:
            return False

    def __getitem__(self, path):
        if not path:
            raise KeyError()

        if path[0] == '/':
            return self.root()[path[1:]]

        part, multi, rest = path.partition("/")

        for child in self.child:
            if child.basename == part:
                break
        else:
            raise KeyError()

        if not multi:
            return child
        else:
            return child[rest]

    @property
    def name(self):
        if self.parent:
            return '/'.join([self.parent.name, self.basename])
        else:
            return self.basename

    def has_descendent(self, node):
        if not self.name or node.name == self.name:
            return True

        if not node.name.startswith(self.name):
            return False

        # make sure that the node is an actual descendent
        # not a different gear with the same prefix in its name
        child_part = node.name.split(self.name, 1)[1]
        return child_part.startswith(('/', '.'))
