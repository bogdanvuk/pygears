from .node_base import SVGenDefaultNode
from .intf_base import SVGenIntfBase


class SVGenModuleBase(SVGenDefaultNode):
    def __init__(self, module, context, parent):
        self.module = module
        self.meta_config = module.meta_config
        outtypes = module.get_type()
        if not isinstance(outtypes, tuple):
            outtypes = (outtypes, )

        single_dout = (len(outtypes) == 1)
        if 'outnames' in self.meta_config[1]:
            outnames = self.meta_config[1]['outnames']
        else:
            outnames = [
                "dout" if single_dout else f"dout{i}"
                for i in range(len(outtypes))
            ]

        super().__init__(context, parent, module.basename)

        for i, (name, ft) in enumerate(zip(module.argnames, module.ftypes[:-1])):
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
    def __init__(self, intf, context, parent):
        super().__init__(
            context, parent, name='', type_=intf.type, producer=None)
        self.intf = intf
        self.index = intf.index
        self.type = self.intf.type
