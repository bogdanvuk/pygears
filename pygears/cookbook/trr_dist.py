from pygears import gear
from pygears.conf import gear_log
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue


def trr_dist_type(dtype):
    return Queue[dtype[0]]


@gear
async def trr_dist(din: Queue, *,
                   dout_num) -> b'(trr_dist_type(din), ) * dout_num':
    t_din = din.dtype

    for i in range(dout_num):
        out_res = [None] * dout_num
        val = t_din((0, 0, 0))

        while (val.eot[0] == 0):
            async with din as val:
                out_res[i] = val[:-1]
                gear_log().debug(
                    f'Trr_dist yielding on output {i} value {out_res[i]}')
                yield tuple(out_res)

        if val.eot == int('1' * t_din.lvl, 2):
            gear_log().debug(f'Trr_dist reset to first output')
            break


class SVGenTrrDist(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(__file__, "trr_dist.j2", context)


class SVGenTrrDistPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][trr_dist] = SVGenTrrDist
