from pygears.lib.sieve import sieve
from pygears.hdl.v import VGenPlugin
from pygears.hdl.v.vmod import VModuleInst
from pygears.hdl.sv.modules.sieve import get_sieve_stages

class VGenSieve(VModuleInst):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'stages': get_sieve_stages(self.node),
            'module_name': self.module_name,
            'intfs': list(self.port_configs)
        }

        return template_env.render_local(__file__, "sieve.j2", context)


class VGenSievePlugin(VGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['vgen']['module_namespace'][sieve] = VGenSieve
