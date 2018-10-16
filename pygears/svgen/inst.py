import os
import logging

from pygears import PluginBase, registry
from pygears.core.hier_node import HierVisitorBase
from pygears.conf import CustomLog
from pygears.definitions import USER_SVLIB_DIR
from pygears.svgen.intf import SVIntfGen


class SVGenInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = registry('svgen/module_namespace')
        self.svgen_map = registry('svgen/map')

    def RTLNode(self, node):
        svgen_cls = node.params['svgen']['svgen_cls']

        if svgen_cls:
            svgen_inst = svgen_cls(node)
        else:
            svgen_inst = None

        self.svgen_map[node] = svgen_inst

    def RTLIntf(self, intf):
        self.svgen_map[intf] = SVIntfGen(intf)


def svgen_inst(top, conf):
    # if 'outdir' in conf:
    #     registry('SVGenSystemVerilogPaths').append(conf['outdir'])

    v = SVGenInstVisitor()
    v.visit(top)

    return top


def register_sv_paths(*paths):
    for p in paths:
        registry('svgen/sv_paths').append(
            os.path.abspath(os.path.expandvars(os.path.expanduser(p))))


def svgen_log():
    return logging.getLogger('svgen')


class SVGenInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        if 'svgen' not in cls.registry:
            cls.registry['svgen'] = {}
        cls.registry['svgen']['map'] = {}
        cls.registry['svgen']['module_namespace'] = {}
        cls.registry['svgen']['sv_paths'] = [USER_SVLIB_DIR]
        CustomLog('svgen', logging.WARNING)

    @classmethod
    def reset(cls):
        cls.registry['svgen']['map'] = {}
