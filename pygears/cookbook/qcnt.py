from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears import gear
from pygears.typing import Queue, Uint

@gear(svgen={'svmod_fn': 'qcnt.sv'})
def qcnt(din: Queue, *, lvl = 1, w_out=16) -> Queue[Uint['w_out']]:
    pass

class SVGenQcnt(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'lvl' : self.node.params['lvl']
        }
        print(self.node.params);
        return template_env.render_local(__file__, "qcnt.j2", context)


class SVGenQcntPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][qcnt] = SVGenQcnt
