from pygears import reg
from pygears.hdl.sv import SVGenPlugin
from pygears.hdl.sv.svmod import SVModuleInst
from pygears.lib.union import union_sync
from .syncguard import SVGenSyncGuard


class SVGenUnionSyncBase(SVModuleInst):
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
    def is_generated(self):
        return True

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


class SVGenUnionPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        reg['svgen/module_namespace'][union_sync] = SVGenUnionSync
