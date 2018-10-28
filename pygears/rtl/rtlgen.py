from pygears import PluginBase, find, registry, safe_bind
from pygears.rtl.channel import RTLChannelVisitor, RTLOutChannelVisitor
from pygears.rtl.connect import rtl_connect
from pygears.rtl.inst import rtl_inst


def rtlgen(top=None, **conf):

    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    for oper in registry('rtl/flow'):
        top = oper(top, conf)

    return top


class RTLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind(
            'rtl/flow',
            [rtl_inst, rtl_connect, RTLChannelVisitor, RTLOutChannelVisitor])
