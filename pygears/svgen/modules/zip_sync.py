from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import zip_sync


class SVGenZipSync(SVGenGearBase):
    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            cfg['lvl'] = type_.lvl
        else:
            cfg['lvl'] = 0

        return cfg

    def get_module(self, template_env):
        intfs = list(self.sv_port_configs())
        queue_intfs = [
            i for i in intfs if i['lvl'] > 0 and i['modport'] == 'consumer'
        ]

        data_intfs = [
            i for i in intfs
            if i['width'] - i['lvl'] > 0 and i['modport'] == 'consumer'
        ]

        context = {
            'queue_intfs': queue_intfs,
            'data_intfs': data_intfs,
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "zip_sync.j2", context)


class SVGenZipSyncPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][zip_sync] = SVGenZipSync
