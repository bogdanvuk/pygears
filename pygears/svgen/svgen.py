from pygears.conf import PluginBase, bind, registry, safe_bind
from pygears.rtl.inst import rtl_inst
from pygears.rtl.connect import rtl_connect
from pygears.rtl.channel import RTLChannelVisitor, RTLOutChannelVisitor
from pygears.util.find import find
from .generate import svgen_generate
from .inst import svgen_inst


def svgen(top=None, **conf):

    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    bind('svgen/conf', conf)
    for oper in registry('svgen/flow'):
        top = oper(top, conf)

    return top


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('svgen/conf', {})
        safe_bind('svgen/flow', [
            rtl_inst, rtl_connect, RTLChannelVisitor, RTLOutChannelVisitor,
            svgen_inst, svgen_generate
        ])
        safe_bind('svgen/module_namespace', {})
        safe_bind('svgen/map', {})
