import inspect
import os

from pygears import PluginBase, registry, safe_bind, config
from pygears.core.hier_node import HierVisitorBase
from .intf import VIntfGen
from pygears.definitions import LIB_VLIB_DIR, USER_VLIB_DIR


class VGenInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = registry('vgen/module_namespace')
        self.vgen_map = registry('vgen/map')

    def RTLGear(self, node):
        if 'hdl' not in node.params:
            node.params['hdl'] = {}

        if 'vgen_cls' not in node.params['hdl']:
            vgen_cls = self.namespace.get(node.gear.definition, None)

            if vgen_cls is None:
                for base_class in inspect.getmro(node.gear.__class__):
                    if base_class.__name__ in self.namespace:
                        vgen_cls = self.namespace[base_class.__name__]
                        break

            node.params['hdl']['vgen_cls'] = vgen_cls

    def RTLNode(self, node):
        vgen_cls = node.params['hdl']['vgen_cls']

        if vgen_cls:
            svgen_inst = vgen_cls(node)
        else:
            svgen_inst = None

        self.vgen_map[node] = svgen_inst

    def RTLIntf(self, intf):
        self.vgen_map[intf] = VIntfGen(intf)


def vgen_inst(top, conf):
    config['hdl/include'].extend([USER_VLIB_DIR, LIB_VLIB_DIR])

    v = VGenInstVisitor()
    v.visit(top)

    return top


class VGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('vgen/map', {})
        safe_bind('vgen/module_namespace', {})

    @classmethod
    def reset(cls):
        safe_bind('vgen/map', {})
