from pygears import module
from pygears.core.gear import gear
from pygears.conf import gear_log
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue


@gear
async def trr(*din: Queue['t_data']) -> b'Queue[t_data, 2]':
    for i, d in enumerate(din):
        val = din[0].dtype((0, 0))
        while (val.eot == 0):
            async with d as val:
                dout = module().tout((val.data, val.eot, (i == len(din) - 1)))
                gear_log().debug(f'Trr yielding {dout}')
                yield dout


class SVGenTrr(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(__file__, "trr.j2", context)


class SVGenTrrPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][trr] = SVGenTrr
