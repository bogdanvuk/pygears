from pygears.core.gear import gear
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen


@gear
async def priority_mux_valve(*din) -> b'Union[din]':
    pass


class SVGenPriorityMuxValve(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(__file__, "priority_mux_valve.j2",
                                         context)


class SVGenPriorityMuxValvePlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][
            priority_mux_valve] = SVGenPriorityMuxValve
