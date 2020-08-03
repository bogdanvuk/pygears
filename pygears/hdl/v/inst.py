import inspect
import os

from pygears import PluginBase, reg
from pygears.core.hier_node import HierVisitorBase
from .intf import VIntfGen
from pygears.definitions import LIB_VLIB_DIR, USER_VLIB_DIR


class VGenInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = reg['vgen/module_namespace']
        self.vgen_map = reg['vgen/map']

    def RTLGear(self, node):
        if 'hdl' not in node.meta_kwds:
            node.meta_kwds['hdl'] = {}

        if 'vgen_cls' not in node.meta_kwds['hdl']:
            vgen_cls = self.namespace.get(node.gear.definition, None)

            if vgen_cls is None:
                for base_class in inspect.getmro(node.gear.__class__):
                    if base_class.__name__ in self.namespace:
                        vgen_cls = self.namespace[base_class.__name__]
                        break

            node.meta_kwds['hdl']['vgen_cls'] = vgen_cls

    def RTLNode(self, node):
        vgen_cls = node.meta_kwds['hdl']['vgen_cls']

        if vgen_cls:
            svgen_inst = vgen_cls(node)
        else:
            svgen_inst = None

        self.vgen_map[node] = svgen_inst

    def RTLIntf(self, intf):
        self.vgen_map[intf] = VIntfGen(intf)


def vgen_inst(top, conf):
    v = VGenInstVisitor()
    v.visit(top)

    return top


def vgen_include_get(cfg):
    return reg['hdl/include'] + [USER_VLIB_DIR, LIB_VLIB_DIR]


class VGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        pass
        # reg['vgen/map'] = {}
        # reg['vgen/module_namespace'] = {}
        # reg.confdef('vgen/include', getter=vgen_include_get)

    @classmethod
    def reset(cls):
        reg['vgen/map'] = {}
