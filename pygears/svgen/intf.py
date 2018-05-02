from pygears.rtl.port import InPort, OutPort


class SVIntfGen:
    def __init__(self, intf):
        self.intf = intf

    @property
    def basename(self):
        producer_port = self.intf.producer
        port_name = producer_port.basename
        producer_name = producer_port.svmod.basename

        if isinstance(producer_port, InPort):
            return port_name
        elif ((not self.intf.is_broadcast) and self.intf.consumers
              and isinstance(self.intf.consumers[0], OutPort)):
            return self.intf.consumers[0].basename
        elif self.intf.sole_intf:
            return f'{producer_name}_if_s'
        else:
            return f'{producer_name}_{port_name}_if_s'

    @property
    def outname(self):
        if self.intf.is_broadcast:
            return f'{self.basename}_bc'
        else:
            return self.basename

    def get_inst(self, template_env):
        if self.intf.producer is None:
            return

        inst = []
        if not self.intf.is_port_intf:
            inst.append(self.get_intf_def(self.basename, 1, template_env))

        if self.intf.is_broadcast:
            inst.extend([
                self.get_intf_def(self.outname, len(self.intf.consumers),
                                  template_env),
                self.get_bc_module(template_env)
            ])

            for i, cons_port in enumerate(self.intf.consumers):
                if isinstance(cons_port, OutPort):
                    inst.append(self.get_connect_module(i, template_env))

        return '\n'.join(inst)

    def get_intf_def(self, name, size, template_env):
        ctx = {
            'name': name,
            'width': int(self.intf.dtype),
            'size': size,
            'type': str(self.intf.dtype)
        }

        return template_env.snippets.intf_inst(**ctx)

    def get_connect_module(self, index, template_env):
        inst_name = f'connect_{self.basename}'
        din_name = self.outname
        if self.intf.is_broadcast:
            inst_name += f'_{index}'
            din_name += f'[{index}]'

        connect_context = {
            'module_name': 'connect',
            'inst_name': inst_name,
            'param_map': {},
            'port_map': {
                'din': din_name,
                'dout': self.intf.consumers[index].basename
            }
        }

        return template_env.snippets.module_inst(**connect_context)

    def get_bc_module(self, template_env):
        inst_name = f'bc_{self.basename}'
        if inst_name.endswith('_if_s'):
            inst_name = inst_name[:-len('_if_s')]
        bc_context = {
            'module_name': 'bc',
            'inst_name': inst_name,
            'param_map': {
                'SIZE': len(self.intf.consumers)
            },
            'port_map': {
                'din': self.basename,
                'dout': self.outname
            }
        }

        return template_env.snippets.module_inst(**bc_context)
