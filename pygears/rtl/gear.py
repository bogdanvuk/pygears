from pygears.rtl.node import RTLNode
from pygears.rtl.intf import RTLIntf
from pygears.core.port import InPort
from pygears.core.hier_node import HierNode
from pygears import registry, PluginBase, safe_bind
from pygears.conf import inject, Inject
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


@inject
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
