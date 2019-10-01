from pygears.rtl.gear import RTLGearHierVisitor
from pygears.rtl import flow_visitor, RTLPlugin


@flow_visitor
class RemoveTupleFlattenVisitor(RTLGearHierVisitor):
    def flatten_tuple(self, node):
        node.bypass()


class RTLFlattenPlugin(RTLPlugin):
    @classmethod
    def bind(cls):
        cls.registry['rtl']['flow'].append(RemoveTupleFlattenVisitor)
