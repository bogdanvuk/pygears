from pygears.registry import PluginBase, bind, registry
from .inst import svgen_inst
from .connect import svgen_connect
from .generate import svgen_generate


def svgen(top=None, **conf):

    if top is None:
        top = registry('HierRoot')

    bind('SVGenConf', conf)
    for oper in registry('SVGenFlow'):
        top = oper(top, conf)

    return top




class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SVGenConf'] = {}
        cls.registry['SVGenFlow'] = [svgen_inst, svgen_connect, svgen_generate]
