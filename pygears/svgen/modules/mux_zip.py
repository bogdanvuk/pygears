from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.mux_zip import mux_zip


class SVGenMuxZip(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):

        intf_cfgs = list(self.sv_port_configs())
        context = {
            'module_name': self.sv_module_name,
            'intfs': intf_cfgs
        }
        return template_env.render_local(__file__, "mux_zip.j2", context)


class SVGenMux_ZipPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][mux_zip] = SVGenMuxZip
