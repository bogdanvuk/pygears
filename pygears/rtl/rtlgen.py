from pygears import PluginBase, find, registry, safe_bind
from pygears.rtl.channel import RTLChannelVisitor, RTLOutChannelVisitor, RTLSigChannelVisitor
from pygears.rtl.connect import rtl_connect
from pygears.rtl.inst import rtl_inst


def rtlgen(top=None, **conf):

    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    if top in registry('rtl/gear_node_map'):
        return registry('rtl/gear_node_map')[top]

    for oper in registry('rtl/flow'):
        top = oper(top, conf)

    return top


class RTLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('rtl/flow', [
            rtl_inst, rtl_connect, RTLChannelVisitor, RTLSigChannelVisitor,
            RTLOutChannelVisitor
        ])
