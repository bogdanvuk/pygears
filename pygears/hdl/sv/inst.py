import inspect
import logging

from pygears import PluginBase, reg
from pygears.conf import register_custom_log
from pygears.core.hier_node import HierVisitorBase
from .intf import SVIntfGen
from pygears.definitions import LIB_SVLIB_DIR, USER_SVLIB_DIR, USER_VLIB_DIR, LIB_VLIB_DIR
from pygears.conf import inject, Inject


class SVGenInstVisitor(HierVisitorBase):
    @inject
    def __init__(self, ext=Inject('hdl/lang')):
        self.namespace = reg[f'{ext}gen/module_namespace']
        self.hdlgen_map = reg[f'{ext}gen/map']

    def Gear(self, node):
        hdlgen_cls = self.namespace.get(node.definition, None)

        if hdlgen_cls is None:
            for base_class in inspect.getmro(node.__class__):
                if base_class.__name__ in self.namespace:
                    hdlgen_cls = self.namespace[base_class.__name__]
                    break

        if hdlgen_cls:
            hdlgen_inst = hdlgen_cls(node)
        else:
            hdlgen_inst = None

        self.hdlgen_map[node] = hdlgen_inst

        if not hdlgen_inst.hierarchical:
            return True

        for i in node.local_intfs:
            self.hdlgen_map[i] = SVIntfGen(i)


def svgen_inst(top, conf):
    v = SVGenInstVisitor()
    v.visit(top)

    return top


def svgen_log():
    return logging.getLogger('hdlgen')


def svgen_include_get(cfg):
    return reg['hdl/include'] + [USER_SVLIB_DIR, LIB_SVLIB_DIR]

def vgen_include_get(cfg):
    return reg['hdl/include'] + [USER_VLIB_DIR, LIB_VLIB_DIR]


class SVGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['svgen/map'] = {}
        register_custom_log('svgen', logging.WARNING)
        reg.confdef('svgen/include', getter=svgen_include_get)

        reg['vgen/map'] = {}
        register_custom_log('vgen', logging.WARNING)
        reg.confdef('vgen/include', getter=vgen_include_get)

    @classmethod
    def reset(cls):
        reg['svgen/map'] = {}
        reg['vgen/map'] = {}
