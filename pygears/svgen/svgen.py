from pygears.registry import PluginBase, bind, registry
from .inst import svgen_inst


def svgen(top, outdir, **conf):
    bind('SVGenConf', conf)
    for oper in registry('SVGenFlow'):
        top = oper(top)


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SVGenConf'] = {}
        cls.registry['SVGenFlow'] = [svgen_inst]
