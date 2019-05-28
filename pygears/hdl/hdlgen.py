from pygears.conf import PluginBase, bind, registry, safe_bind
from pygears.rtl import rtlgen
from pygears.util.find import find


def find_rtl_top(top, **conf):
    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    rtl_map = registry('rtl/gear_node_map')
    if top not in rtl_map:
        rtlgen(**conf)

    return rtl_map[top]


def hdlgen(top=None, language='sv', **conf):
    rtl_top = find_rtl_top(top, **conf)

    bind('svgen/conf', conf)
    for oper in registry(f'{language}gen/flow'):
        rtl_top = oper(rtl_top, conf)

    return rtl_top
