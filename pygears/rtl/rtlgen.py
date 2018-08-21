from pygears.registry import PluginBase
from pygears import registry, find
from pygears.rtl.inst import rtl_inst
from pygears.rtl.connect import rtl_connect
from pygears.rtl.channel import RTLChannelVisitor, RTLOutChannelVisitor


def rtlgen(top=None, **conf):

    if top is None:
        top = registry('HierRoot')
    elif isinstance(top, str):
        top = find(top)

    for oper in registry('RTLFlow'):
        top = oper(top, conf)

    return top


class RTLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['RTLFlow'] = [
            rtl_inst, rtl_connect, RTLChannelVisitor, RTLOutChannelVisitor
        ]
