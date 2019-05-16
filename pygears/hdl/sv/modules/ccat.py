from pygears.hdl.sv import SVGenPlugin
from pygears.common.ccat import ccat
from pygears.hdl.sv.svmod import SVModuleGen


class SVGenCCat(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.module_name,
            'intfs': list(self.port_configs)
        }

        return template_env.render_local(__file__, "ccat.j2", context)


class SVGenCCatPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][ccat] = SVGenCCat
