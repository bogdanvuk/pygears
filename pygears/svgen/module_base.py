from pygears.svgen.node_base import SVGenDefaultNode
from pygears.svgen.intf_base import SVGenIntfBase


class SVGenModuleBase(SVGenDefaultNode):
    def __init__(self, module, parent):
        self.module = module
        outtypes = module.get_type()
        if not isinstance(outtypes, tuple):
            outtypes = (outtypes, )

        single_dout = (len(outtypes) == 1)
        if 'outnames' in self.module.params:
            outnames = self.module.params['outnames']
        else:
            outnames = [
                "dout" if single_dout else f"dout{i}"
                for i in range(len(outtypes))
            ]

        super().__init__(parent, module.basename)

        for i, (name, ft) in enumerate(
                zip(module.argnames, module.get_arg_types())):
            self.add_port(name, 'in', None, ft, i)

        for i, (name, ft) in enumerate(zip(outnames, outtypes)):
            if ft is not None:
                self.add_port(name, 'out', None, ft, i)

    def connect(self):
        self.intfs = []
        for a, p in zip(self.module.args, self.in_ports()):
            self.connect_intf(p, self.context.svgens.get(a))

        for i, p in zip(self.module.intfs, self.out_ports()):
            self.connect_intf(p, self.context.svgens.get(i))


class SVGenIntfModuleBase(SVGenIntfBase):
    def __init__(self, intf, parent):
        super().__init__(parent, name='', type_=intf.type, producer=None)
        self.intf = intf
        self.index = intf.index
        self.type = self.intf.type
