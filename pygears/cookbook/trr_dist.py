from pygears import gear
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue


def trr_dist_type(dtype):
    return Queue[dtype[0]]


@gear
async def trr_dist(din, *, dout_num) -> b'(trr_dist_type(din), ) * dout_num':
    for i in range(dout_num):
        out_res = [None] * dout_num
        val = (0, ) * din.dtype.lvl
        while (val[1] == 0):
            async with din as val:
                out_res[i] = val[:-1]
                # print(f'Trr_dist: yielding {tuple(out_res)}')
                yield tuple(out_res)


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
        cls.registry['SVGenModuleNamespace'][trr_dist] = SVGenTrrDist
