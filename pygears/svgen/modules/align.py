from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.common.align import align


class SVGenAlign(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        params = {}

        from pygears.typing import Queue
        for l, p in zip(self.node.params['lvl'], self.node.in_ports):
            dtype = p.dtype
            if issubclass(dtype, Queue):
                dtype = dtype[0]
            params[f'W_{p.basename.upper()}_LVL'] = l
            params[f'W_{p.basename.upper()}_DATA'] = int(dtype)

        context = {
            'module_name': self.sv_module_name,
            'params': params,
            'intfs': list(self.sv_port_configs())
        }
        return template_env.render_local(__file__, "align.j2", context)


class SVGenAlignPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][align] = SVGenAlign
