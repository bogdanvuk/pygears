from pygears import gear
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue, Uint


def chunk_type(dtypes):
    return Queue[dtypes[0]]


@gear
def chunk_concat(cfg: Uint['Tn'], *din: 'w_din{0}',
                 cnt_type=0) -> b'chunk_type(din)':
    pass


class SVGenChunkConcat(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'cnt_type': self.node.params['cnt_type']
        }
        return template_env.render_local(__file__, "chunk_concat.j2", context)


class SVGenChunkConcatPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][chunk_concat] = SVGenChunkConcat
