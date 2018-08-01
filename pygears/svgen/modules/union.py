from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.common.union import union_sync
from .syncguard import SVGenSyncGuard


class SVGenUnionSyncBase(SVModuleGen):
    def __init__(self, node):
        super().__init__(node)

        if 'outsync' not in self.node.params:
            self.node.params['outsync'] = True

        if self.node.params['outsync']:
            self.syncguard = SVGenSyncGuard(f'{self.sv_module_name}_syncguard',
                                            len(self.node.in_ports))
        else:
            self.syncguard = None

    @property
    def is_generated(self):
        return True

    @property
    def sv_file_name(self):
        if self.syncguard is None:
            return super().sv_file_name
        else:
            return super().sv_file_name, self.syncguard.sv_file_name

    def get_module(self, template_env, template_fn):

        context = {
            'outsync': self.node.params['outsync'],
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'ctrl': self.node.params['ctrl']
        }
        contents = template_env.render_local(__file__, template_fn, context)

        if self.syncguard is None:
            return contents
        else:
            return contents, self.syncguard.get_module(template_env)


class SVGenUnionSync(SVGenUnionSyncBase):
    def get_module(self, template_env):

        return super().get_module(template_env, 'union_sync.j2')


class SVGenUnionPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][union_sync] = SVGenUnionSync
