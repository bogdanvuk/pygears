import os
import inspect
from pygears.core.hier_node import HierYielderBase
from pygears.core.gear import Gear


class NodeYielder(HierYielderBase):
    def Gear(self, node):
        yield node

def _py_file_enum_raw(top):
    for node in NodeYielder().visit(top):
        if not isinstance(node, Gear):
            continue

        yield os.path.abspath(inspect.getfile(node.func))

        for t in node.trace:
            yield os.path.abspath(inspect.getframeinfo(t[0]).filename)


def py_files_enum(top):
    for fn in _py_file_enum_raw(top):
        if '<decorator-gen' not in fn:
            yield fn
