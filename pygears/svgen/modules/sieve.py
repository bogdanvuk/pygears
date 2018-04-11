from pygears.common import sieve
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.module_base import SVGenGearBase
from functools import partial


def index_to_sv_slice(dtype, index):
    subtype = dtype[index]

    if isinstance(index, slice):
        index = index.start

    if index is None or index == 0:
        low_pos = 0
    else:
        low_pos = int(dtype[:index])

    high_pos = low_pos + int(subtype) - 1

    return f'{high_pos}:{low_pos}'


class SVGenSieve(SVGenGearBase):
    def get_module(self, template_env):
        dtype = self.in_ports[0].dtype
        context = {
            'indexes':
            map(
                partial(index_to_sv_slice, dtype),
                filter(lambda i: int(dtype[i]) > 0, self.params['index'])),
            'module_name':
            self.sv_module_name,
            'intfs':
            list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "sieve.j2", context)


class SVGenSievePlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][sieve] = SVGenSieve
