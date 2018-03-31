from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import zip_sync
from .syncguard import SVGenSyncGuard


class SVGenZipSync(SVGenGearBase):
    def __init__(self, gear, parent):
        super().__init__(gear, parent)

        if 'outsync' not in self.params:
            self.params['outsync'] = True

        if self.params['outsync']:
            SVGenSyncGuard(self, f'{self.sv_module_name}_syncguard',
                           len(gear.in_ports))

    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            cfg['lvl'] = type_.lvl
        else:
            cfg['lvl'] = 0

        return cfg

    def get_module(self, template_env):

        context = {
            'outsync': self.params['outsync'],
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "zip_sync.j2", context)


class SVGenZipSyncPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][zip_sync] = SVGenZipSync
