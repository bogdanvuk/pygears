from pygears.conf import PluginBase, bind, registry, safe_bind
from pygears.rtl import rtlgen
from pygears.util.find import find
from .generate import svgen_generate
from .inst import svgen_inst


def svgen(top=None, **conf):

    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    rtl_map = registry('rtl/gear_node_map')
    if top not in rtl_map:
        rtlgen(**conf)

    rtl_top = rtl_map[top]

    bind('svgen/conf', conf)
    for oper in registry('svgen/flow'):
        rtl_top = oper(rtl_top, conf)

    return rtl_top


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('svgen/conf', {})
        safe_bind('svgen/flow', [svgen_inst, svgen_generate])
        safe_bind('svgen/module_namespace', {})
        safe_bind('svgen/map', {})
