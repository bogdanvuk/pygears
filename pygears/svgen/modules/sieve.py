from pygears.common import sieve
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.module_base import SVGenGearBase


class SVGenSieve(SVGenGearBase):
    def get_module(self, template_env):
        def index_to_sv_slice(index):
            if isinstance(index, slice):
                return f'{index.stop-1}:{index.start}'
            else:
                return f'{index}'

        context = {
            'indexes': map(index_to_sv_slice, self.params['index']),
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "sieve.j2", context)


class SVGenSievePlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][sieve] = SVGenSieve
