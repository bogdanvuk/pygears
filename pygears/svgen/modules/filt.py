from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.common.filt import filt


class SVGenFilt(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'sel': self.node.params['sel']
        }
        return template_env.render_local(__file__, "filt.j2", context)


class SVGenFiltPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][filt] = SVGenFilt
