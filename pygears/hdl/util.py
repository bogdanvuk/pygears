from pygears.core.hier_node import HierVisitorBase

class HDLGearHierVisitor(HierVisitorBase):
    def RTLGear(self, node):
        gear = node.gear
        if hasattr(self, gear.definition.__name__):
            return getattr(self, gear.definition.__name__)(node)


def flow_visitor(cls):
    def svgen_action(top, conf):
        v = cls()
        v.conf = conf
        v.visit(top)
        return top

    return svgen_action


def is_gear_instance(node, definition):
    return node.gear.definition is definition
