from pygears.hdl.sv.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.hdl.sv import SVGenPlugin
from pygears.common.czip import zip_sync, zip_cat
from .syncguard import SVGenSyncGuard
from .cat_util import din_data_cat


class SVGenCZipBase(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_port_config(self, modport, type_, name):
        cfg = super().get_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            cfg['lvl'] = type_.lvl
        else:
            cfg['lvl'] = 0

        return cfg


class SVGenZipCat(SVGenCZipBase):
    def get_module(self, template_env):
        intfs = list(self.port_configs)
        queue_intfs = [
            i for i in intfs if i['lvl'] > 0 and i['modport'] == 'consumer'
        ]

        context = {
            'queue_intfs': queue_intfs,
            'module_name': self.module_name,
            'intfs': list(self.port_configs),
            'din_data_cat': din_data_cat
        }

        return template_env.render_local(__file__, "zip_cat.j2", context)


class SVGenZipSyncBase(SVGenCZipBase):
    def __init__(self, node):
        super().__init__(node)

        if 'outsync' not in self.node.params:
            self.node.params['outsync'] = True

        if self.node.params['outsync']:
            self.syncguard = SVGenSyncGuard(f'{self.module_name}_syncguard',
                                            len(self.node.in_ports))
        else:
            self.syncguard = None

    @property
    def file_name(self):
        if self.syncguard is None:
            return super().file_name
        else:
            return super().file_name, self.syncguard.file_name

    def get_module(self, template_env, template_fn):

        context = {
            'outsync': self.node.params['outsync'],
            'module_name': self.module_name,
            'intfs': list(self.port_configs)
        }
        contents = template_env.render_local(__file__, template_fn, context)

        if self.syncguard is None:
            return contents
        else:
            return contents, self.syncguard.get_module(template_env)


class SVGenZipSync(SVGenZipSyncBase):
    def get_module(self, template_env):
        if all(map(lambda i: i['lvl'] > 0, self.port_configs)):
            return super().get_module(template_env, 'zip_sync.j2')
        else:
            return super().get_module(template_env, 'zip_sync_simple.j2')


class SVGenCZipPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][zip_sync] = SVGenZipSync
        cls.registry['svgen']['module_namespace'][zip_cat] = SVGenZipCat
