from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.mux import mux


class SVGenMux(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):

        intf_cfgs = list(self.sv_port_configs())
        context = {
            'module_name': self.sv_module_name,
            'intfs': intf_cfgs
        }
        return template_env.render_local(__file__, "mux.j2", context)


class SVGenMuxPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][mux] = SVGenMux
