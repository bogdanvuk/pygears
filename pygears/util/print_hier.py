import pprint
from pygears.core.hier_node import HierVisitorBase
import textwrap
from pygears.conf import util_log, inject, Inject


def module_signature(module, fullname, params):
    t = module.tout
    if t is None:
        types = "None"
        sizes = ""
    elif isinstance(t, tuple):
        types = ', '.join([str(tt) for tt in t])
        sizes = ', '.join([str(tt.width) for tt in t])
    else:
        types = str(t)
        sizes = t.width

    if fullname:
        name = module.name
    else:
        name = module.basename

    return f'{name}: {types} ({sizes})'


class Visitor(HierVisitorBase):
    omitted = ['definition', 'sim_setup']

    def __init__(self, params=False, fullname=False):
        self.indent = ""
        self.params = params
        self.fullname = fullname
        self.res = []
        self.pp = pprint.PrettyPrinter(indent=4, width=120)

    def Gear(self, node):
        self.print_module_signature(node)
        self.indent += "    "
        super().HierNode(node)
        self.indent = self.indent[:-4]
        return True

    def print_module_signature(self, module):
        def get_size(t):
            try:
                return str(t.width)
            except TypeError:
                return '?'

        t = module.tout
        if t is None:
            types = "None"
            sizes = ""
        elif isinstance(t, tuple):
            types = ', '.join([str(tt) for tt in t])
            sizes = ', '.join([get_size(tt) for tt in t])
        else:
            types = str(t)
            sizes = get_size(t)

        if self.fullname:
            name = module.name
        else:
            name = module.basename

        self.res.append(f'{self.indent}{name}: {types} ({sizes})')
        if self.params:
            params = {
                p: repr(v)
                for p, v in module.params.items() if p not in self.omitted
            }

            p = self.pp.pformat(params)
            # print(p)
            self.res.append(textwrap.indent(p, self.indent))
            # self.res.append(f'{self.indent}    {p}')


@inject
def print_hier(root=Inject('gear/root'), params=False, fullname=False):
    v = Visitor(params, fullname)
    v.visit(root)
    util_log().info('\n'.join(v.res))
