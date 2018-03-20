from pygears.registry import PluginBase, bind, registry
from .inst import svgen_inst
from .connect import svgen_connect
from pygears.registry import load_plugin_folder
import os


def svgen(top, outdir, **conf):
    bind('SVGenConf', conf)
    for oper in registry('SVGenFlow'):
        top = oper(top)

    return top


load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SVGenConf'] = {}
        cls.registry['SVGenFlow'] = [svgen_inst, svgen_connect]
