from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import mux


class SVGenMux(SVModuleGen):
    def get_module(self, template_env):

        intf_cfgs = list(self.sv_port_configs())
        for i, p in zip(intf_cfgs, self.node.in_ports):
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
        return template_env.render_local(__file__, "mux.j2", context)


class SVGenMuxPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][mux] = SVGenMux
