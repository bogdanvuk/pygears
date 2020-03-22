import inspect
import logging

from pygears import PluginBase, registry, safe_bind, config
from pygears.conf import register_custom_log
from pygears.core.hier_node import HierVisitorBase
from .intf import SVIntfGen
from pygears.definitions import LIB_SVLIB_DIR, USER_SVLIB_DIR


class SVGenInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = registry('svgen/module_namespace')
        self.svgen_map = registry('svgen/map')

    def Gear(self, node):
        svgen_cls = self.namespace.get(node.definition, None)

        if svgen_cls is None:
            for base_class in inspect.getmro(node.__class__):
                if base_class.__name__ in self.namespace:
                    svgen_cls = self.namespace[base_class.__name__]
                    break

        if svgen_cls:
            svgen_inst = svgen_cls(node)
        else:
            svgen_inst = None

        self.svgen_map[node] = svgen_inst

        if not svgen_inst.hierarchical:
            return True

        for i in node.local_intfs:
            self.svgen_map[i] = SVIntfGen(i)


def svgen_inst(top, conf):
    v = SVGenInstVisitor()
    v.visit(top)

    return top


def svgen_log():
    return logging.getLogger('svgen')


def svgen_include_get(cfg):
    return config['hdl/include'] + [USER_SVLIB_DIR, LIB_SVLIB_DIR]


class SVGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('svgen/map', {})
        register_custom_log('svgen', logging.WARNING)

        config.define('svgen/include', getter=svgen_include_get)

    @classmethod
    def reset(cls):
        safe_bind('svgen/map', {})
