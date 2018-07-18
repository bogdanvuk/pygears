from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.demux import demux_zip
from .syncguard import SVGenSyncGuard


class SVGenDemuxZip(SVModuleGen):
    def __init__(self, node):
        super().__init__(node)
        self.syncguard = SVGenSyncGuard(f'{self.sv_module_name}_syncguard', 2)

    @property
    def is_generated(self):
        return True

    @property
    def sv_file_name(self):
        return super().sv_file_name, self.syncguard.sv_file_name

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(
            __file__, "demux_zip.j2", context), \
            self.syncguard.get_module(template_env)


class SVGenDemuxZipPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][demux_zip] = SVGenDemuxZip
