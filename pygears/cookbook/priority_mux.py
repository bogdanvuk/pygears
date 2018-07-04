from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears.core.gear import alternative, gear
from pygears.typing import Union
from pygears import module
from pygears.sim import clk


# TODO: why is b' necessary in return expression?
@gear
async def priority_mux(*din) -> b'Union[din]':
    for i, d in enumerate(din):
        if not d.empty():
            async with d as item:
                yield module().tout((item, i))
    await clk()


class SVGenPriorityMux(SVModuleGen):
    @property
    def is_generated(self):
        return True

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
