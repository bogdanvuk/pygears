from pygears.conf import PluginBase, reg
from .generate import svgen_generate
from .v.generate import vgen_generate
from .inst import svgen_inst
from .svmod import SVModuleInst
from .resolvers import HDLFileResolver, HDLTemplateResolver, HierarchicalResolver, HLSResolver, BlackBoxResolver
from pygears.conf import PluginBase, reg


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['svgen/flow'] = [svgen_inst, svgen_generate]
        reg['svgen/resolvers'] = [
            HDLFileResolver, HDLTemplateResolver, HLSResolver,
            HierarchicalResolver
        ]
        reg['svgen/dflt_resolver'] = BlackBoxResolver

        reg['svgen/module_namespace'] = {
            'Gear': SVModuleInst,
            'GearHierRoot': SVModuleInst
        }

        reg['vgen/module_namespace'] = {
            'Gear': SVModuleInst,
            'GearHierRoot': SVModuleInst
        }

        reg['vgen/flow'] = [svgen_inst, vgen_generate]
        reg['vgen/resolvers'] = [
            HDLFileResolver, HDLTemplateResolver, HLSResolver,
            HierarchicalResolver
        ]
        reg['vgen/dflt_resolver'] = BlackBoxResolver


from pygears.conf import load_plugin_folder
import os
load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

__all__ = ['svgen_generate']
