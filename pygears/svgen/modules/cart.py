from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.queue import Queue
from pygears.typing.uint import Uint
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.cart import lvl_if_queue


class SVGenCart(SVGenGearBase):
    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)
        struct_type = type_

        fields = []
        if issubclass(type_, Queue):
            lvl = type_.lvl
            type_ = type_[0]
            cfg['data_eot'] = f'(&{name}_s.eot)'
        else:
            lvl = 0
            cfg['data_eot'] = 1

        if int(type_) > 0:
            fields.append({
                'name': 'data',
                'svtype': None,
                'type': Uint[int(type_)]
            })

        if lvl > 0:
            fields.append({'name': 'eot', 'svtype': None, 'type': Uint[lvl]})

        cfg['lvl'] = lvl
        cfg['struct'] = {
            'name': name,
            'type': struct_type,
            'subtypes': fields,
            'svtype': 'struct'
        }

        return cfg

    def get_module(self, template_env):
        stmts = []
        din_lvl = [lvl_if_queue(p.dtype) for p in self.in_ports]
        max_lvl = max(din_lvl)
        self.eot_type = Uint[max_lvl]
        queue_intfs = [
            p for p in self.sv_port_configs()
            if p['lvl'] > 0 and p['modport'] == 'consumer'
        ]

        data_intfs = [
            p for p in self.sv_port_configs()
            if p['width'] - p['lvl'] > 0 and p['modport'] == 'consumer'
        ]

        context = {
            'statements': stmts,
            'max_lvl': max_lvl,
            'queue_intfs': queue_intfs,
            'data_intfs': data_intfs,
            'max_lvl_din': self.in_ports[din_lvl.index(max_lvl)],
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "cart.j2", context)


class SVGenCartPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Cart'] = SVGenCart
