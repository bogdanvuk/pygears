from pygears.core.port import InPort
from pygears.conf import reg_inject, Inject
from pygears.rtl.intf import RTLIntf
from pygears.core.hier_node import HierVisitorBase


def gear_from_rtl_port(rtl_port):
    node = rtl_port.node
    return node.gear.in_ports[rtl_port.index]


@reg_inject
def rtl_from_gear_port(gear_port, rtl_map=Inject('rtl/gear_node_map')):
    node = rtl_map.get(gear_port.gear, None)
    rtl_port = None
    if node:
        if isinstance(gear_port, InPort):
            port_group = node.in_ports
        else:
            port_group = node.out_ports

        rtl_port = port_group[gear_port.index]

    return rtl_port


@reg_inject
def connect(node, rtl_map=Inject('rtl/gear_node_map')):
    for p, gear_p in zip(node.in_ports, node.gear.in_ports):
        create_intf(p, gear_p, domain=node)
        prod_intf = gear_p.producer
        if (node.parent is not None and prod_intf is not None
                and prod_intf.producer is None):
            create_unsourced_intf(node, p, gear_p)

    for p, gear_p in zip(node.out_ports, node.gear.out_ports):
        create_intf(p, gear_p, domain=node.parent)
        gear_intf = gear_p.consumer

        if (node.parent is not None and gear_intf is not None
                and not gear_intf.consumers):

            node.root().add_out_port(p.basename, dtype=p.dtype)
            rtl_map[gear_intf].connect(node.root().out_ports[-1])


@reg_inject
def create_unsourced_intf(node,
                          port,
                          gear_port,
                          rtl_map=Inject('rtl/gear_node_map')):
    gear_intf = gear_port.producer
    consumers = []
    for cons_port in gear_intf.consumers:
        rtl_port = rtl_from_gear_port(cons_port)
        if rtl_port:
            consumers.append(rtl_port)

    intf_inst = RTLIntf(node.root(), gear_intf.dtype, consumers=consumers)

    node.root().add_in_port(port.basename,
                            dtype=intf_inst.dtype,
                            consumer=intf_inst)

    intf_inst.producer = node.root().in_ports[-1]

    for cons_port in consumers:
        cons_port.producer = intf_inst

    rtl_map[gear_intf] = intf_inst


@reg_inject
def create_intf(port, gear_port, domain, rtl_map=Inject('rtl/gear_node_map')):
    gear_intf = gear_port.consumer
    if gear_intf is not None:
        consumers = []
        for cons_port in gear_intf.consumers:
            rtl_port = rtl_from_gear_port(cons_port)
            if rtl_port:
                consumers.append(rtl_port)

        intf_inst = RTLIntf(domain,
                            gear_intf.dtype,
                            producer=port,
                            consumers=consumers)

        if hasattr(gear_intf, 'var_name'):
            intf_inst.var_name = gear_intf.var_name

        for cons_port in consumers:
            cons_port.producer = intf_inst

        rtl_map[gear_intf] = intf_inst
        port.consumer = intf_inst


class RTLConnectVisitor(HierVisitorBase):
    def RTLGear(self, rtl_gear):
        super().HierNode(rtl_gear)
        connect(rtl_gear)
        return True


def rtl_connect(top, conf):
    v = RTLConnectVisitor()
    v.visit(top)
    return top
