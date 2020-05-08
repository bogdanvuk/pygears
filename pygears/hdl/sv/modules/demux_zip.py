from pygears import reg
from pygears.hdl.sv.svmod import SVModuleInst
from pygears.hdl.sv import SVGenPlugin
from pygears.lib.demux import demux_zip
from .syncguard import SVGenSyncGuard


class SVGenDemuxZip(SVModuleInst):
    def __init__(self, node):
        super().__init__(node)
        self.syncguard = SVGenSyncGuard(f'{self.module_name}_syncguard', 2)

    @property
    def is_generated(self):
        return True

    @property
    def file_name(self):
        return super().file_name, self.syncguard.file_name

    def get_module(self, template_env):
        context = {
            'module_name': self.module_name,
            'intfs': list(self.port_configs)
        }
        return template_env.render_local(
            __file__, "demux_zip.j2", context), \
            self.syncguard.get_module(template_env)


class SVGenDemuxZipPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        reg['svgen/module_namespace'][demux_zip] = SVGenDemuxZip
