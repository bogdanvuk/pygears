import inspect
import logging
import os

from pygears import PluginBase, reg
from pygears.conf import register_custom_log
from pygears.core.hier_node import HierVisitorBase
from .intf import SVIntfGen
from pygears.definitions import LIB_SVLIB_DIR, USER_SVLIB_DIR, USER_VLIB_DIR, LIB_VLIB_DIR
from pygears.conf import inject, Inject
from pygears.hdl import hdlmod, list_hdl_files


class SVGenInstVisitor(HierVisitorBase):
    def Gear(self, node):
        hdlgen_inst = hdlmod(node)

        if not hdlgen_inst.hierarchical:
            return True

        for i in node.local_intfs:
            hdlgen_map = reg['hdlgen/map']
            hdlgen_map[i] = SVIntfGen(i, hdlgen_inst.lang)


def svgen_inst(top, conf):
    v = SVGenInstVisitor()
    v.visit(top)

    list_hdl_files(top.name,
                   outdir=conf['outdir'],
                   rtl_only=True,
                   wrapper=conf.get('wrapper', False))

    # hdlmods = reg['hdlgen/hdlmods']
    # for fn in list_hdl_files(top, conf['outdir'], wrapper=conf.get('wrapper', False)):
    #     modname, lang = os.path.splitext(os.path.basename(fn))
    #     hdlmods[(modname, lang[1:])] = fn


def svgen_log():
    return logging.getLogger('hdlgen')


def svgen_include_get(cfg):
    return reg['hdl/include'] + [USER_SVLIB_DIR, LIB_SVLIB_DIR]


def vgen_include_get(cfg):
    return reg['hdl/include'] + [USER_VLIB_DIR, LIB_VLIB_DIR]


class SVGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['hdlgen/map'] = {}
        reg['hdlgen/hdlmods'] = {}
        reg['hdlgen/disambig'] = {}
        register_custom_log('svgen', logging.WARNING)
        reg.confdef('svgen/include', getter=svgen_include_get)
        reg.confdef('vhdgen/include', [])

        reg['vgen/map'] = {}
        register_custom_log('vgen', logging.WARNING)
        reg.confdef('vgen/include', getter=vgen_include_get)

    @classmethod
    def reset(cls):
        reg['vgen/map'] = {}
        reg['hdlgen/hdlmods'] = {}
        reg['hdlgen/disambig'] = {}
