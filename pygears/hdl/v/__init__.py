from pygears.conf import PluginBase
from .generate import vgen_generate
from .inst import vgen_inst
from .vmod import VModuleInst
from pygears.conf import PluginBase, reg

from .vcompile import compile_gear, compile_gear_body


class VGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        pass
        # reg['vgen/flow'] = [vgen_inst, vgen_generate]
        # reg['vgen/resolvers'] = 
        #     HDLFileResolver, HDLTemplateResolver, HLSResolver,
        #     HierarchicalResolver
        # ])

        # reg['svgen/dflt_resolver'] = BlackBoxResolver
        # # reg['vgen/flow'] = [vgen_inst]
        # reg['vgen/module_namespace'] = {}
        # reg['vgen/module_namespace/Gear'] = VModuleInst
        # reg['vgen/module_namespace/GearHierRoot'] = VModuleInst

__all__ = ['compile_gear', 'compile_gear_body']
