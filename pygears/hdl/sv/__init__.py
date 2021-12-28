import os

from pygears.conf import PluginBase, reg
from .inst import svgen_inst
from .svmod import SVModuleInst
from .resolvers import HDLFileResolver, HDLTemplateResolver, HierarchicalResolver, HLSResolver, BlackBoxResolver
from pygears.conf import PluginBase, reg

from pygears.hdl.templenv import TemplateEnv
from .v.util import vgen_intf, vgen_signal
from .util import svgen_typedef


class SVTemplateEnv(TemplateEnv):
    lang = 'sv'

    def __init__(self):
        super().__init__(basedir=os.path.dirname(__file__))

        self.jenv.globals.update(svgen_typedef=svgen_typedef)

        self.snippets = self.load(self.basedir, 'snippet.j2').module


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['svgen/flow'] = [svgen_inst]
        reg['svgen/resolvers'] = [
            HDLFileResolver, HDLTemplateResolver, HierarchicalResolver, HLSResolver
        ]
        reg['svgen/dflt_resolver'] = BlackBoxResolver
        reg['svgen/templenv'] = SVTemplateEnv()

        reg['svgen/module_namespace'] = {'Gear': SVModuleInst, 'GearHierRoot': SVModuleInst}


class VTemplateEnv(TemplateEnv):
    lang = 'v'

    def __init__(self):
        super().__init__(basedir=os.path.join(os.path.dirname(__file__), 'v'))

        self.jenv.globals.update(vgen_intf=vgen_intf, vgen_signal=vgen_signal)

        self.snippets = self.load(self.basedir, 'snippet.j2').module


class VGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['vgen/templenv'] = VTemplateEnv()

        reg['vgen/module_namespace'] = {'Gear': SVModuleInst, 'GearHierRoot': SVModuleInst}

        reg['vgen/flow'] = [svgen_inst]
        reg['vgen/resolvers'] = [
            HDLFileResolver,
            HDLTemplateResolver,
            HierarchicalResolver,
            HLSResolver,
        ]
        reg['vgen/dflt_resolver'] = BlackBoxResolver


from pygears.conf import load_plugin_folder
import os

load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

__all__ = ['svgen_generate']
