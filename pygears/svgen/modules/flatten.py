from pygears.rtl.gear import RTLGearHierVisitor
from pygears.svgen.inst import SVGenInstPlugin, svgen_inst
from pygears.svgen.util import svgen_visitor


@svgen_visitor
class RemoveTupleFlattenVisitor(RTLGearHierVisitor):
    def flatten_tuple(self, node):
        node.bypass()


class SVGenFlattenPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['flow'].insert(
            cls.registry['svgen']['flow'].index(svgen_inst),
            RemoveTupleFlattenVisitor)
