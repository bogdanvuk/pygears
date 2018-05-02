from pygears import registry, PluginBase
from pygears.core.hier_node import HierVisitorBase, NamedHierNode, HierNode
from pygears.rtl.gear import RTLGearNodeGen
import inspect


class RTLNodeDesign(NamedHierNode):
    def __init__(self):
        super().__init__('')


class RTLNodeGearRoot(HierNode):
    def __init__(self, module):
        super().__init__()
        self.node = RTLNodeDesign()
        self.module = module

    def out_port_make(self, port, node):
        print(
            f'Module {node.name} has unconnected output port {port["name"]}.')

    def in_port_make(self, port, node):
        print(f'Module {node.name} has unconnected input port {port["name"]}.')


class RTLNodeInstVisitor(HierVisitorBase):
    def __init__(self):
        self.cur_hier = None
        self.design = None
        self.namespace = registry('RTLGearGenNamespace')
        self.svgen_map = registry('RTLNodeMap')

    def NamedHierNode(self, module):
        self.design = RTLNodeGearRoot(module)
        self.cur_hier = self.design

    def instantiate(self, module):
        svgen = module.params.get('svgen', {})
        node_cls = svgen.get('node_cls', None)

        if node_cls is None:
            node_cls = self.namespace.get(module.definition, None)

        if node_cls is None:
            for base_class in inspect.getmro(module.__class__):
                if base_class.__name__ in self.namespace:
                    node_cls = self.namespace[base_class.__name__]
                    break

        if node_cls:
            svgen_inst = node_cls(module, parent=self.cur_hier)
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


def rtl_inst(top, conf):
    v = RTLNodeInstVisitor()
    v.visit(top)

    return v.design


class RTLNodeInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['RTLNodeNamespace'] = {}
        cls.registry['RTLGearGenNamespace'] = {
            'Gear': RTLGearNodeGen,
            'Hier': RTLGearNodeGen
        }
        cls.registry['RTLNodeMap'] = {}

    @classmethod
    def reset(cls):
        cls.registry['RTLNodeMap'] = {}
