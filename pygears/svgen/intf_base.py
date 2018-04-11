from pygears.core.hier_node import NamedHierNode
from pygears.core.port import InPort, OutPort


class SVGenIntfBase(NamedHierNode):
    def __init__(self, parent, type_, producer=None, consumers=[]):
        super().__init__(basename=None, parent=parent)
        self.consumers = consumers.copy()
        self.producer = producer
        self.type = type_

    @property
    def sole_intf(self):
        if self.producer:
            return len(self.producer.gear.out_ports) == 1
        else:
            return True

    @property
    def is_broadcast(self):
        return len(self.consumers) > 1

    @property
    def basename(self):
        producer_port = self.producer
        port_name = producer_port.basename
        producer_name = producer_port.gear.basename

        if isinstance(producer_port, InPort):
            return port_name
        elif ((not self.is_broadcast) and self.consumers
              and isinstance(self.consumers[0], OutPort)):
            return self.consumers[0].basename
        elif self.sole_intf:
            return f'{producer_name}_if_s'
        else:
            return f'{producer_name}_{port_name}_if_s'

    @property
    def is_port_intf(self):
        if isinstance(self.producer, InPort):
            return True
        elif ((not self.is_broadcast) and self.consumers
              and isinstance(self.consumers[0], OutPort)):
            return True
        else:
            return False

    @property
    def outname(self):
        if self.is_broadcast:
            return f'{self.basename}_bc'
        else:
            return self.basename

    def disconnect(self, port):
        if port in self.consumers:
            self.consumers.remove(port)
            port.producer = None
        elif port == self.producer:
            port.consumer = None
            self.producer = None

    def connect(self, port):
        self.consumers.append(port)
        port.producer = self

    def get_inst(self, template_env):
        if self.producer is None:
            return

        inst = []
        if not self.is_port_intf:
            inst.append(self.get_intf_def(self.basename, 1, template_env))

        if self.is_broadcast:
            inst.extend([
                self.get_intf_def(self.outname, len(self.consumers),
                                  template_env),
                self.get_bc_module(template_env)
            ])

            for i, cons_port in enumerate(self.consumers):
                if isinstance(cons_port, OutPort):
                    inst.append(self.get_connect_module(i, template_env))

        return '\n'.join(inst)

    def get_intf_def(self, name, size, template_env):
        ctx = {
            'name': name,
            'width': int(self.type),
            'size': size,
            'type': str(self.type)
        }

        return template_env.snippets.intf_inst(**ctx)

    def get_connect_module(self, index, template_env):
        inst_name = f'connect_{self.basename}'
        din_name = self.outname
        if self.is_broadcast:
            inst_name += f'_{index}'
            din_name += f'[{index}]'

        connect_context = {
            'module_name': 'connect',
            'inst_name': inst_name,
            'param_map': {},
            'port_map': {
                'din': din_name,
                'dout': self.consumers[index].basename
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
                'SIZE': len(self.consumers)
            },
            'port_map': {
                'din': self.basename,
                'dout': self.outname
            }
        }

        return template_env.snippets.module_inst(**bc_context)
