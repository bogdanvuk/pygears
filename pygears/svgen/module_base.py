from pygears import registry
from pygears.svgen.intf_base import SVGenIntfBase
from pygears.svgen.node_base import SVGenDefaultNode
from pygears.svgen.port import InPort, OutPort
import itertools


def reconnect_port(gear_port, port):
    iin = gear_port.producer
    iout = gear_port.consumer

    if iin:
        iin.disconnect(gear_port)
        iin.connect(port)

    if iout:
        iout.disconnect(gear_port)
        iout.source(port)


class SVGenGearBase(SVGenDefaultNode):
    def __init__(self, gear, parent):
        in_ports = [InPort(self, p) for p in gear.in_ports]
        out_ports = [OutPort(self, p) for p in gear.out_ports]

        for gear_port, port in zip(
                itertools.chain(gear.in_ports, gear.out_ports),
                itertools.chain(in_ports, out_ports)):
            reconnect_port(gear_port, port)

        super().__init__(parent, gear.basename, in_ports, out_ports)

        self.gear = gear
        self.params = gear.params
        self.__doc__ = gear.__doc__

    def create_intf(self, port, domain):
        intf = port.consumer
        if intf is not None:
            intf_inst = SVGenIntfModuleBase(intf, port, parent=domain)
            self.svgen_map[intf] = intf_inst
            port.consumer = intf_inst

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
            svmod = cons_port.node
            if isinstance(cons_port, InPort):
                port_group = svmod.in_ports
            else:
                port_group = svmod.out_ports

            svgen_port = port_group[cons_port.index]
            consumers.append(svgen_port)
            svgen_port.producer = self

        super().__init__(
            parent, type_=intf.dtype, producer=port, consumers=consumers)
        self.intf = intf

    @property
    def dtype(self):
        return self.intf.dtype
