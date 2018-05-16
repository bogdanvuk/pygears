from pygears.svgen.svmod import SVModuleGen
from pygears.typing.queue import Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.cart import cart


class SVGenCartBase(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            cfg['lvl'] = type_.lvl
            cfg['data_eot'] = f'(&{name}_s.eot)'
        else:
            cfg['lvl'] = 0
            cfg['data_eot'] = 1

        return cfg


class SVGenCart(SVGenCartBase):
    @property
    def is_generated(self):
        return True

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
            'intfs': intfs
        }

        return template_env.render_local(__file__, "cart.j2", context)


class SVGenCartPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][cart] = SVGenCart
