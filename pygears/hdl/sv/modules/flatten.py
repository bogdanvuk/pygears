from pygears.hdl.util import HDLGearHierVisitor, flow_visitor
# from pygears.rtl import flow_visitor, RTLPlugin


@flow_visitor
class RemoveTupleFlattenVisitor(HDLGearHierVisitor):
    def flatten_tuple(self, node):
        node.bypass()


# class RTLFlattenPlugin(RTLPlugin):
#     @classmethod
#     def bind(cls):
#         cls.registry['rtl']['flow'].append(RemoveTupleFlattenVisitor)
