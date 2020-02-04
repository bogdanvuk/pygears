from pygears.core.port import InPort, HDLConsumer, HDLProducer
from pygears.conf import inject, Inject
from pygears.rtl.intf import RTLIntf
from pygears.core.hier_node import HierVisitorBase
from pygears.core.graph import rtl_from_gear_port


def gear_from_rtl_port(rtl_port):
    node = rtl_port.node
    return node.gear.in_ports[rtl_port.index]


@inject
def connect(node, rtl_map=Inject('rtl/gear_node_map')):
    for p, gear_p in zip(node.in_ports, node.gear.in_ports):
        if not node.is_hierarchical:
            p.consumer = None
        else:
            create_intf(p, gear_p, domain=node)

        prod_intf = gear_p.producer

        if isinstance(prod_intf.producer, HDLProducer):
            intf_inst = RTLIntf(node.parent, prod_intf.dtype, producer=HDLProducer())
            intf_inst.connect(p)
            rtl_map[prod_intf] = intf_inst
            continue

        # If this port was already connected while processing other ports (it
        # shares an interface with them)
        if isinstance(p.producer, RTLIntf):
            continue

        if (node.parent is not None and prod_intf is not None
                and prod_intf.producer is None):
            create_unsourced_intf(node, p, gear_p)

    for p, gear_p in zip(node.out_ports, node.gear.out_ports):
        gear_intf = gear_p.consumer

        if (len(gear_intf.consumers) == 1 and isinstance(gear_intf.consumers[0], HDLConsumer)):
            intf_inst = RTLIntf(node.parent, gear_intf.dtype, producer=p)
            rtl_map[gear_intf] = intf_inst
        else:
            create_intf(p, gear_p, domain=node.parent)

        if not node.is_hierarchical:
            p.producer = None


        if (node.parent is not None and gear_intf is not None
                and not gear_intf.consumers):

            node.root().add_out_port(p.basename, dtype=p.dtype)
            rtl_map[gear_intf].connect(node.root().out_ports[-1])


@inject
def create_unsourced_intf(node,
                          port,
                          gear_port,
                          rtl_map=Inject('rtl/gear_node_map')):
    gear_intf = gear_port.producer

    intf_inst = RTLIntf(node.root(), gear_intf.dtype)
    for cons_port in gear_intf.consumers:
        rtl_port = rtl_from_gear_port(cons_port)
        if rtl_port:
            intf_inst.connect(rtl_port)

    node.root().add_in_port(port.basename,
                            dtype=intf_inst.dtype,
                            consumer=intf_inst)

    intf_inst.producer = node.root().in_ports[-1]

    rtl_map[gear_intf] = intf_inst


@inject
def create_intf(port, gear_port, domain, rtl_map=Inject('rtl/gear_node_map')):
    gear_intf = gear_port.consumer
    if not isinstance(gear_intf, HDLConsumer):
        intf_inst = RTLIntf(domain, gear_intf.dtype, producer=port)

        for cons_port in gear_intf.consumers:
            rtl_port = rtl_from_gear_port(cons_port)
            if rtl_port:
                intf_inst.connect(rtl_port)

        if hasattr(gear_intf, 'var_name'):
            intf_inst.var_name = gear_intf.var_name

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
