from collections import OrderedDict
from pygears.svgen.module_base import SVGenModuleBase
from pygears.typing.queue import Queue, QueueMeta
from pygears.typing.uint import Uint
from pygears.core.concat import arg_is_delim, lvl_if_queue
from .svstruct import field_def, compose


class SVGenConcat(SVGenModuleBase):
    def get_params(self):
        pexclude = ['queue_pack']
        params = OrderedDict([(p.upper(), int(v))
                              for p, v in self.module.params.items()
                              if p not in pexclude])

        is_queue = [lvl_if_queue(p['type']) for p in self.in_ports()]
        # is_queue = [isinstance(t['type'], QueueMeta) for t in self.in_ports()]
        for p, isq in zip(self.ports, is_queue):
            params[f'{p["name"].upper()}_EOT_WIDTH'] = int(isq)

        return params

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

    def get_module_stmts(self):

        snippet = self.context.snippets

        is_queue = [isinstance(t['type'], QueueMeta) for t in self.in_ports()]
        is_delim = [arg_is_delim(t['type']) for t in self.in_ports()]

        for p in self.in_ports():
            yield from self.get_module_intf_decl(p['type'], p['name'])

        if self.module.params['queue_pack']:
            out_data = [
                f'{p["name"]}_data' for p in reversed(list(self.in_ports()))
                if int(p['type']) > 0
            ]
        else:
            out_data = [
                f'{p["name"]}.data' for p in reversed(list(self.in_ports()))
                if int(p['type']) > 0
            ]

        din_align = ['1'] * len(list(self.in_ports()))

        if all(is_queue):
            # If all inputs are queues, zip operation is performed
            out_data.insert(0, f'din0_eot')
        elif any(is_queue) and is_delim[-1] and (not all(is_delim)):
            # If one input is a Queue and the other is delimiter is_delim[-1]
            # is only possible for now, since delimiters are produced by Queue
            # Fmap only, and this Fmap places delimiters in line 1 only
            out_data.insert(1, 'din0_eot')
            din_align[0] = '&din0_eot'
        else:
            # Only some of the inputs are queues
            for i, isq in enumerate(is_queue):
                if isq:
                    if self.module.params['queue_pack']:
                        out_data.insert(0, f'din{i}_eot')

                    din_align[i] = f'&din{i}_eot'

        yield snippet.assign('dout.data', snippet.concat(out_data))
        for p, da in zip(self.in_ports(), din_align):
            yield snippet.assign(f'{p["name"]}_align', da)

    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        if issubclass(type_, Queue):
            lvl = type_.lvl
            type_ = type_[0]
            fields = [
                field_def('data', Uint[int(type_)]),
                field_def('eot', Uint[lvl])
            ]
        else:
            lvl = 0
            fields = [field_def('data', Uint[int(type_)])]

        cfg['lvl'] = lvl
        cfg['struct'] = compose(name, type_, fields)

        return cfg

    def get_module(self):
        # stmts = list(self.get_module_stmts())
        stmts = []
        din_lvl = [lvl_if_queue(p['type']) for p in self.in_ports()]
        max_lvl = max(din_lvl)
        self.eot_type = Uint[max_lvl]
        queue_intfs = [
            p for p in self.sv_port_configs()
            if p['lvl'] > 0 and p['modport'] == 'consumer'
        ]

        # dout_valid_elems = [f'{p["name"].dvalid}' for p in self.in_ports()]

        return self.context.jenv.get_template("concat.j2").render(
            statements=stmts,
            max_lvl=max_lvl,
            queue_intfs=queue_intfs,
            max_lvl_din=list(self.in_ports())[din_lvl.index(max_lvl)],
            module_name=self.sv_module_name,
            intfs=list(self.sv_port_configs()))
