from pygears.registry import PluginBase, bind, registry
from pygears.rtl.inst import rtl_inst
from pygears.rtl.connect import rtl_connect
from pygears.rtl.channel import RTLChannelVisitor, RTLOutChannelVisitor
from pygears.util.find import find
from .generate import svgen_generate
from .inst import svgen_inst


def svgen(top=None, **conf):

    if top is None:
        top = registry('HierRoot')
    elif isinstance(top, str):
        top = find(top)

    bind('SVGenConf', conf)
    for oper in registry('SVGenFlow'):
        top = oper(top, conf)

    return top


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SVGenConf'] = {}
        cls.registry['SVGenFlow'] = [
            rtl_inst, rtl_connect, RTLChannelVisitor, RTLOutChannelVisitor, svgen_inst,
            svgen_generate
        ]
