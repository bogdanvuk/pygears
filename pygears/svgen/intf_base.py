from pygears.core.hier_node import NamedHierNode
from collections import OrderedDict


class SVGenIntfBase(NamedHierNode):
    def __init__(self,
                 context,
                 parent,
                 name,
                 type_,
                 producer=None,
                 implicit=False,
                 consumers=set()):
        super().__init__(name, parent)
        self.consumers = consumers.copy()
        self.producer = producer
        self.context = context
        self.implicit = implicit
        self.type = type_

    @property
    def sole_intf(self):
        if self.producer:
            return len(list(self.producer[0].out_ports())) == 1
        else:
            return True

    @property
    def inname(self):
        if self.basename:
            return self.basename
        elif self.sole_intf:
            name = f'{self.producer[0].basename}'
        else:
            for i, p in enumerate(self.producer[0].out_ports()):
                if p['intf'] == self:
                    pname = p['name']
                    break

            name = f'{self.producer[0].basename}_{pname}'

        if not self.implicit:
            name += "_if_s"

        return name

    @property
    def outname(self):
        if len(self.consumers) > 1:
            return f'{self.inname}_bc'
        else:
            return self.inname

    def get_inst(self):
        if self.producer is None:
            return

        inst = []
        if not self.implicit:
            inst.append(self.get_intf_def(self.inname, 1))

        if len(self.consumers) > 1:
            inst.extend([
                self.get_intf_def(self.outname, len(self.consumers)),
                self.get_bc_module()
            ])

        return '\n'.join(inst)

    def get_intf_def(self, name, size):
        ctx = {
            'name': name,
            'width': int(self.type),
            'size': size,
            'type': str(self.type)
        }

        return self.context.jenv.get_template('snippet.j2').module.intf_inst(
            **ctx)

    def get_bc_module(self):
        inst_name = f'bc_{self.inname}'
        if inst_name.endswith('_if_s'):
            inst_name = inst_name[:-len('_if_s')]
        bc_context = {
            'module_name': 'bc',
            'inst_name': inst_name,
            'param_map': OrderedDict([('NUM_OF_PRODUCERS',
                                       len(self.consumers))]),
            'port_map': OrderedDict([('din', self.inname), ('dout',
                                                            self.outname)])
        }

        return self.context.jenv.get_template('snippet.j2').module.module_inst(
            **bc_context)
