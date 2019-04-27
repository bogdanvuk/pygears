from pygears.rtl.node import RTLNode
from pygears.rtl.intf import RTLIntf
from pygears.core.port import InPort
from pygears.core.hier_node import HierNode
from pygears import registry, PluginBase, safe_bind
from pygears.conf import reg_inject, Inject
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


class RTLGearNodeGen(HierNode):
    @reg_inject
    def __init__(self, gear, parent, rtl_map=Inject('rtl/gear_node_map')):
        super().__init__(parent)
        self.rtl_map = rtl_map

        if isinstance(gear, RTLGear):
            self.gear = gear.gear
            self.node = gear
            parent_node = getattr(parent, "node", None)
            if parent_node:
                parent_node.add_child(self.node)
        else:
            self.gear = gear
            self.node = RTLGear(gear, getattr(parent, "node", None))
            self.rtl_map[gear] = self.node

            namespace = registry('svgen/module_namespace')

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
                self.node.add_in_port(p.basename, p.producer, p.consumer,
                                      p.dtype)

            for p in gear.out_ports:
                self.node.add_out_port(p.basename, p.producer, p.consumer,
                                       p.dtype)

