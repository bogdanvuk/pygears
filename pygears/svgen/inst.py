from pygears import PluginBase, registry
from pygears.core.hier_node import HierVisitorBase, NamedHierNode
from pygears.core.gear import HierRootPlugin


class SVGenDesign(NamedHierNode):
    def __init__(self, module, context):
        super().__init__('')
        self.context = context
        self.module = module

    def out_port_make(self, port, node):
        print(
            f'Module {node.name} has unconnected output port {port["name"]}.')

    def in_port_make(self, port, node):
        print(f'Module {node.name} has unconnected input port {port["name"]}.')


class SVGenInstVisitor(HierVisitorBase):
    def __init__(self, context):
        self.context = context
        self.cur_hier = None

    def NamedHierNode(self, module):
        self.cur_hier = SVGenDesign(module, self.context)
        return True

    def Hier(self, module):
        self.cur_hier = SVGenHier(module, self.context, parent=self.cur_hier)
        self.context.svgens[module] = self.cur_hier
        super().HierNode(module)
        self.cur_hier = self.cur_hier.parent
        return True

    def Gear(self, module):
        svgen_cls = registry('SVGenModuleNamespace').get(
            type(module).__name__, None)

        if not svgen_cls:
            svgen_cls = module.params['svgen']

        if svgen_cls:
            self.context.svgens[module] = svgen_cls(
                module, self.context, parent=self.cur_hier)

        return True


def svgen_inst(top):
    pass


class SVGenInstPlugin(PluginBase, HierRootPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'] = {}
        cls.registry['GearMetaParams']['svgen'] = None
