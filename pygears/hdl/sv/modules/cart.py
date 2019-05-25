from pygears.hdl.sv.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.hdl.sv import SVGenPlugin
from pygears.common.cart import cart, cart_sync
from .syncguard import SVGenSyncGuard
from .cat_util import din_data_cat


class SVGenCartBase(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_port_config(self, modport, type_, name):
        cfg = super().get_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            cfg['lvl'] = type_.lvl
            cfg['data_eot'] = f'(&{name}_s.eot)'
        else:
            cfg['lvl'] = 0
            cfg['data_eot'] = 1

        return cfg


class SVGenCartSyncBase(SVGenCartBase):
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
            'intfs': list(self.port_configs),
            'din_data_cat': din_data_cat
        }
        contents = template_env.render_local(__file__, template_fn, context)

        if self.syncguard is None:
            return contents
        else:
            return contents, self.syncguard.get_module(template_env)


class SVGenCartSync(SVGenCartSyncBase):
    def get_module(self, template_env):

        return super().get_module(template_env, 'cart_sync.j2')


class SVGenCartPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][cart_sync] = SVGenCartSync
