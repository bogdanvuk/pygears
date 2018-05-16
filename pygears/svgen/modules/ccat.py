from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.ccat import ccat
from pygears.svgen.svmod import SVModuleGen


class SVGenCCat(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "ccat.j2", context)


class SVGenCCatPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][ccat] = SVGenCCat
