from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.queue import Queue
from pygears.typing.uint import Uint
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.czip import lvl_if_queue


class SVGenCZip(SVGenGearBase):
    def get_module_intf_decl(self, ftype, intf):
        snippet = self.context.snippets
        intf_w = f'{intf.upper()}_WIDTH'
        intf_eot_w = f'{intf.upper()}_EOT_WIDTH'
        intf_data_w_high = f'{intf_w}-{intf_eot_w}-1'

        yield snippet.logic(f'{intf}_data', intf_data_w_high)
        data_rng = self.context.snippets.range(f'{intf}.data',
                                               intf_data_w_high)
        yield snippet.assign(f'{intf}_data', data_rng)

        # if isinstance(ftype, QueueMeta):
        if issubclass(ftype, Queue):
            yield snippet.logic(f'{intf}_eot', f'{intf_eot_w}-1')

            eot_rng = self.context.snippets.range(
                name=f'{intf}.data',
                high=f'{intf_w}-1',
                low=f'{intf_w}-{intf_eot_w}')

            yield snippet.assign(f'{intf}_eot', eot_rng)

    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            lvl = type_.lvl
            type_ = type_[0]
            fields = [{
                'name': 'data',
                'svtype': None,
                'type': Uint[int(type_)]
            }, {
                'name': 'eot',
                'svtype': None,
                'type': Uint[lvl]
            }]
        else:
            lvl = 0
            fields = [{
                'name': 'data',
                'svtype': None,
                'type': Uint[int(type_)]
            }]

        cfg['lvl'] = lvl
        cfg['struct'] = {
            'name': name,
            'type': type_,
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

        context = {
            'statements': stmts,
            'max_lvl': max_lvl,
            'queue_intfs': queue_intfs,
            'max_lvl_din': self.in_ports[din_lvl.index(max_lvl)],
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "czip.j2", context)


class SVGenCZipPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['CZip'] = SVGenCZip
