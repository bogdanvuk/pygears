from pygears.registry import PluginBase, bind
from .inst import svgen_inst


def svgen(top, outdir, **conf):
    bind('SVGenConf', conf)


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SVGenConf'] = {}
        cls.registry['SVGenFlow'] = [svgen_inst]
