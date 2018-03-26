from pygears import registry
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
        self.design = None
        self.namespace = registry('SVGenModuleNamespace')
        self.svgen_map = registry('SVGenMap')

    def NamedHierNode(self, module):
        self.design = SVGenDesign(module)
        self.cur_hier = self.design

    def instantiate(self, module):
        svgen_cls = module.params['svgen']

        if svgen_cls is None:
            svgen_cls = self.namespace.get(module.definition, None)

        if svgen_cls is None:
            for base_class in inspect.getmro(module.__class__):
                if base_class.__name__ in self.namespace:
                    svgen_cls = self.namespace[base_class.__name__]
                    break

        if svgen_cls:
            svgen_inst = svgen_cls(module, parent=self.cur_hier)
        else:
            svgen_inst = None

        self.svgen_map[module] = svgen_inst

        if self.cur_hier is None:
            self.design = svgen_inst

        return svgen_inst

    def Hier(self, module):
        self.cur_hier = self.instantiate(module)
        super().HierNode(module)
        self.cur_hier = self.cur_hier.parent
        return True

    def Gear(self, module):
        self.instantiate(module)
        return True


def svgen_inst(top, conf):
    v = SVGenInstVisitor()
    v.visit(top)

    return v.design


class SVGenInstPlugin(HierRootPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'] = {}
        cls.registry['GearMetaParams']['svgen'] = None
        cls.registry['SVGenMap'] = {}
