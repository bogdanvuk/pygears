from pygears import registry
from pygears.core.port import InPort
from pygears.svgen.intf_base import SVGenIntfBase
from pygears.svgen.node_base import SVGenDefaultNode
import itertools


class SVGenGearBase(SVGenDefaultNode):
    def __init__(self, gear, parent):
        super().__init__(parent, gear.basename, gear.in_ports, gear.out_ports)
        for p in itertools.chain(self.in_ports, self.out_ports):
            p.gear = self

        self.gear = gear
        self.__doc__ = gear.__doc__

    def create_intf(self, port, domain):
        intf = port.consumer
        if intf is not None:
            intf_inst = SVGenIntfModuleBase(intf, port, parent=domain)
            self.svgen_map[intf] = intf_inst
            port.consumer = intf_inst

            # producer_port = intf.producer
            # # If interface has a producer port, wire its svgen counterpart to
            # # intf_inst
            # if producer_port is not None:
            #     svmod = producer_port.gear
            #     if isinstance(producer_port, InPort):
            #         port_group = svmod.in_ports
            #     else:
            #         port_group = svmod.out_ports

            #     port_group[producer_port.index].consumer = intf_inst

    def connect(self):
        self.svgen_map = registry('SVGenMap')
        for p in self.in_ports:
            self.create_intf(p, domain=self)

        for p in self.out_ports:
            self.create_intf(p, domain=self.parent)


class SVGenIntfModuleBase(SVGenIntfBase):
    def __init__(self, intf, port, parent):
        consumers = []
        for cons_port in intf.consumers:
            svmod = cons_port.gear
            if isinstance(cons_port, InPort):
                port_group = svmod.in_ports
            else:
                port_group = svmod.out_ports

            svgen_port = port_group[cons_port.index]
            consumers.append(svgen_port)
            svgen_port.producer = self

        super().__init__(
            parent,
            type_=intf.dtype,
            producer=port,
            consumers=consumers)
        self.intf = intf

    @property
    def dtype(self):
        return self.intf.dtype
