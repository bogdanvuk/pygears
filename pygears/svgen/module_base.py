from pygears.svgen.node_base import SVGenDefaultNode
from pygears.svgen.intf_base import SVGenIntfBase
from pygears import registry


class SVGenGearBase(SVGenDefaultNode):
    def __init__(self, gear, parent):
        super().__init__(parent, gear.basename, gear.in_ports,
                         gear.out_ports)
        self.gear = gear

    def create_intf(self, port, domain):
        intf = port.producer
        if intf is not None:
            intf_inst = SVGenIntfModuleBase(intf, port, parent=domain)
            self.svgen_map[intf] = intf_inst
            port.producer = intf_inst

    def connect(self):
        self.svgen_map = registry('SVGenMap')
        for p in self.in_ports:
            self.create_intf(p, domain=self)

        for p in self.out_ports:
            self.create_intf(p, domain=self.parent)


class SVGenIntfModuleBase(SVGenIntfBase):
    def __init__(self, intf, port, parent):
        super().__init__(parent, name='', type_=intf.dtype, producer=port)
        self.intf = intf
        # self.index = intf.index
        # self.type = self.intf.type
