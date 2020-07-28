from pygears import reg
from pygears.hdl.sv import SVGenPlugin
from pygears.hdl.sv.svmod import SVModuleInst
from pygears.lib.align import align


class SVGenAlign(SVModuleInst):
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
            params[f'W_{p.basename.upper()}_DATA'] = dtype.width

        context = {
            'module_name': self.module_name,
            'params': params,
            'intfs': list(self.port_configs)
        }
        return template_env.render_local(__file__, "align.j2", context)


class SVGenAlignPlugin(SVGenPlugin):
    @classmethod
    def bind(cls):
        reg['svgen/module_namespace'][align] = SVGenAlign
