from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import demux
from .syncguard import SVGenSyncGuard


class SVGenDemux(SVModuleGen):
    def __init__(self, node):
        super().__init__(node)

        if self.node.params['ctrl_out']:
            self.syncguard = SVGenSyncGuard(f'{self.sv_module_name}_syncguard', 2)
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

    def get_module(self, template_env):
        if self.node.params['ctrl_out']:
            intf_cfgs = list(self.sv_port_configs())
            for i, p in zip(intf_cfgs, self.node.out_ports):
                if issubclass(p.dtype, Queue):
                    i['eot_expr'] = (
                        f'&{i["name"]}.data[$size({i["name"]}.data)-1: '
                        f'$size({i["name"]}.data)-{p["type"].lvl}]')
                else:
                    i['eot_expr'] = 1

            context = {
                'module_name': self.sv_module_name,
                'intfs': intf_cfgs
            }
            return template_env.render_local(__file__, "demux.j2", context), \
                self.syncguard.get_module(template_env)
        else:
            context = {
                'module_name': self.sv_module_name,
                'ctrl_width': int(self.node.in_ports[0].dtype[1]),
                'intfs': list(self.sv_port_configs())
            }
            return template_env.render_local(__file__, "demux.j2", context)


class SVGenDemuxPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][demux] = SVGenDemux
