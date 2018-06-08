from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears.core.gear import alternative, gear
from pygears.typing import Union
import os


def priority_mux_type(dtypes):
    return Union[dtypes]


@gear
def priority_mux(*din) -> b'priority_mux_type(din)':
    pass


class SVGenPriorityMux(SVModuleGen):
    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(__file__, "priority_mux.j2", context)


class SVGenPriorityMuxPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][priority_mux] = SVGenPriorityMux
