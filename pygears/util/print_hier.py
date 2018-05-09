from pygears import registry
from pygears.core.hier_node import HierVisitorBase


class Visitor(HierVisitorBase):
    def __init__(self, params=False, fullname=False):
        self.indent = ""
        self.params = params
        self.fullname = fullname

    def Gear(self, node):
        self.print_module_signature(node)
        self.indent += "    "
        super().HierNode(node)
        self.indent = self.indent[:-4]
        return True

    def print_module_signature(self, module):
        t = module.get_type()
        if t is None:
            types = "None"
            sizes = ""
        elif isinstance(t, tuple):
            types = ', '.join([str(tt) for tt in t])
            sizes = ', '.join([str(int(tt)) for tt in t])
        else:
            types = str(t)
            sizes = int(t)

        if self.fullname:
            name = module.name
        else:
            name = module.basename

        print(f'{self.indent}{name}: {types} ({sizes})')
        if self.params:
            print(
                f'{self.indent}    : {", ".join([p+": "+str(v) for p,v in module.params.items()])}'
            )


def print_hier(root=None, params=False, fullname=False):
    if root is None:
        root = registry('HierRoot')

    Visitor(params, fullname).visit(root)
