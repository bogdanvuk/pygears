from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.inst import svgen_inst
from pygears.rtl.gear import RTLGearHierVisitor, is_gear_instance
from pygears.svgen.svgen import SVGenPlugin, svgen_visitor


@svgen_visitor
class RemoveTupleFlattenVisitor(RTLGearHierVisitor):
    def flatten_tuple(self, node):
        print(node.name)
        node.bypass()


class SVGenFlattenPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(svgen_inst),
            RemoveTupleFlattenVisitor)