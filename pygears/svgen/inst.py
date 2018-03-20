from pygears import PluginBase, registry
from pygears.core.hier_node import HierVisitorBase, NamedHierNode
from pygears.core.gear import HierRootPlugin
import inspect


class SVGenDesign(NamedHierNode):
    def __init__(self, module):
        super().__init__('')
        self.module = module

    def out_port_make(self, port, node):
        print(
            f'Module {node.name} has unconnected output port {port["name"]}.')

    def in_port_make(self, port, node):
        print(f'Module {node.name} has unconnected input port {port["name"]}.')


class SVGenInstVisitor(HierVisitorBase):
    def __init__(self):
        self.cur_hier = None
        self.top = None

    def NamedHierNode(self, module):
        self.top = SVGenDesign(module)
        self.cur_hier = self.top

    def instantiate(self, module):
        svgen_cls = module.params['svgen']

        for base_class in inspect.getmro(module.__class__):
            if base_class.__name__ in registry('SVGenModuleNamespace'):
                svgen_cls = registry('SVGenModuleNamespace')[
                    base_class.__name__]
                break

        if svgen_cls:
            return svgen_cls(module, parent=self.cur_hier)

    def Hier(self, module):
        self.cur_hier = self.instantiate(module)
        super().HierNode(module)
        self.cur_hier = self.cur_hier.parent
        return True

    def Gear(self, module):
        self.instantiate(module)
        return True


def svgen_inst(top):
    v = SVGenInstVisitor()
    v.visit(top)


class SVGenInstPlugin(HierRootPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'] = {}
        cls.registry['GearMetaParams']['svgen'] = None
