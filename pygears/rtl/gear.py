from pygears.rtl.node import RTLNode
from pygears.rtl.intf import RTLIntf
from pygears.core.port import InPort
import itertools
from pygears import registry
from pygears.core.hier_node import HierNode
from pygears import registry, PluginBase
from pygears.core.hier_node import HierVisitorBase
import inspect


class RTLGear(RTLNode):
    def __init__(self, gear, parent):
        super().__init__(parent, gear.basename, params=gear.params)
        self.gear = gear


def is_gear_instance(node, definition):
    if isinstance(node, RTLGear):
        return node.gear.definition is definition

    return False


class RTLGearHierVisitor(HierVisitorBase):
    def RTLGear(self, node):
        gear = node.gear
        if hasattr(self, gear.definition.__name__):
            return getattr(self, gear.definition.__name__)(node)


def rtl_from_gear_port(gear_port):
    node_gen = registry('RTLNodeMap').get(gear_port.gear, None)
    rtl_port = None
    if node_gen:
        node = node_gen.node

        if isinstance(gear_port, InPort):
            port_group = node.in_ports
        else:
            port_group = node.out_ports

        rtl_port = port_group[gear_port.index]

    return rtl_port


class RTLGearNodeGen(HierNode):
    def __init__(self, gear, parent):
        super().__init__(parent)
        self.gear = gear
        self.node = RTLGear(gear, getattr(parent, "node", None))

        namespace = registry('SVGenModuleNamespace')

        if 'svgen' not in self.node.params:
            self.node.params['svgen'] = {}

        if 'svgen_cls' not in self.node.params['svgen']:
            svgen_cls = namespace.get(gear.definition, None)

            if svgen_cls is None:
                for base_class in inspect.getmro(gear.__class__):
                    if base_class.__name__ in namespace:
                        svgen_cls = namespace[base_class.__name__]
                        break

            self.node.params['svgen']['svgen_cls'] = svgen_cls

        for p in gear.in_ports:
            self.node.add_in_port(p.basename, p.producer, p.consumer, p.dtype)

        for p in gear.out_ports:
            self.node.add_out_port(p.basename, p.producer, p.consumer, p.dtype)

    def connect(self):
        self.rtl_map = registry('RTLNodeMap')

        for p, gear_p in zip(self.node.in_ports, self.gear.in_ports):
            self.create_intf(p, gear_p, domain=self.node)
            prod_intf = gear_p.producer
            if (self.node.parent is not None and prod_intf is not None
                    and prod_intf.producer is None):
                self.create_unsourced_intf(p, gear_p)

        for p, gear_p in zip(self.node.out_ports, self.gear.out_ports):
            self.create_intf(p, gear_p, domain=self.node.parent)
            gear_intf = gear_p.consumer
            if self.node.parent is not None and gear_intf is not None and not gear_intf.consumers:
                # intf_inst = RTLIntf(
                #     self.node.root(), gear_intf.dtype)

                self.node.root().add_out_port(p.basename, dtype=p.dtype)

                # intf_inst.producer = self.node.root().out_ports[-1]

                self.rtl_map[gear_intf].connect(self.node.root().out_ports[-1])

    def create_unsourced_intf(self, port, gear_port):
        gear_intf = gear_port.producer
        consumers = []
        for cons_port in gear_intf.consumers:
            rtl_port = rtl_from_gear_port(cons_port)
            if rtl_port:
                consumers.append(rtl_port)

        intf_inst = RTLIntf(
            self.node.root(), gear_intf.dtype, consumers=consumers)

        self.node.root().add_in_port(
            port.basename, dtype=intf_inst.dtype, consumer=intf_inst)

        intf_inst.producer = self.node.root().in_ports[-1]

        for cons_port in consumers:
            cons_port.producer = intf_inst

        self.rtl_map[gear_intf] = intf_inst

    def create_intf(self, port, gear_port, domain):
        gear_intf = gear_port.consumer
        if gear_intf is not None:
            consumers = []
            for cons_port in gear_intf.consumers:
                rtl_port = rtl_from_gear_port(cons_port)
                if rtl_port:
                    consumers.append(rtl_port)

            intf_inst = RTLIntf(
                domain, gear_intf.dtype, producer=port, consumers=consumers)

            if hasattr(gear_intf, 'var_name'):
                intf_inst.var_name = gear_intf.var_name

            for cons_port in consumers:
                cons_port.producer = intf_inst

            self.rtl_map[gear_intf] = intf_inst
            port.consumer = intf_inst


class RTLInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['RTLModuleNamespace'] = {}
        cls.registry['RTLClsMap'] = {}
