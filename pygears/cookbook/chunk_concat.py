from pygears import gear
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue, Uint, Tuple


def chunk_type(dtypes, chunk_size):
    if (chunk_size == 1):
        return Queue[dtypes[0]]
    else:
        return Queue[Tuple[(dtypes[0][0], ) * chunk_size], 2]


@gear
def chunk_concat(cfg: Uint['Tn'],
                 *din: 'w_din{0}',
                 cnt_type=0,
                 chunk_size=1,
                 pad=0) -> b'chunk_type(din, chunk_size)':
    pass


class SVGenChunkConcat(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'cnt_type': self.node.params['cnt_type'],
            'chunk_size': self.node.params['chunk_size'],
            'pad': self.node.params['pad']
        }
        return template_env.render_local(__file__, "chunk_concat.j2", context)


class SVGenChunkConcatPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][
            chunk_concat] = SVGenChunkConcat
