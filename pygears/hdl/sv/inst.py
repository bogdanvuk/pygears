import inspect
import logging

from pygears import PluginBase, reg
from pygears.conf import register_custom_log
from pygears.core.hier_node import HierVisitorBase
from .intf import SVIntfGen
from pygears.definitions import LIB_SVLIB_DIR, USER_SVLIB_DIR, USER_VLIB_DIR, LIB_VLIB_DIR
from pygears.conf import inject, Inject
from pygears.hdl import hdlmod


class SVGenInstVisitor(HierVisitorBase):
    def Gear(self, node):
        hdlgen_inst = hdlmod(node)

        if not hdlgen_inst.hierarchical:
            return True

        for i in node.local_intfs:
            hdlgen_map = reg[f'{hdlgen_inst.lang}gen/map']
            hdlgen_map[i] = SVIntfGen(i, hdlgen_inst.lang)


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
