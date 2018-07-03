from pygears import PluginBase, registry
from pygears.core.hier_node import HierVisitorBase, NamedHierNode, HierNode
from pygears.rtl.gear import RTLGearNodeGen, RTLNode
import inspect


class RTLNodeDesign(RTLNode):
    def __init__(self):
        super().__init__(None, '')


class GearHierRoot(NamedHierNode):
    def __init__(self, root):
        super().__init__('')
        self.in_ports = []
        self.out_ports = []
        self.root = root


class RTLNodeGearRoot(RTLGearNodeGen):
    def __init__(self, module):
        HierNode.__init__(self)
        self.node = RTLNodeDesign()
        self.gear = GearHierRoot(module)

        namespace = registry('SVGenModuleNamespace')
        self.node.params['svgen'] = {'svgen_cls': namespace['RTLNodeDesign']}
        self.module = module

        for p in self.gear.in_ports:
            self.node.add_in_port(p.basename, p.producer, p.consumer, p.dtype)

        for p in self.gear.out_ports:
            self.node.add_out_port(p.basename, p.producer, p.consumer, p.dtype)


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
        # node_cls = svgen.get('node_cls', None)
        if 'node_cls' in svgen:
            node_cls = svgen['node_cls']
        else:
            node_cls = self.namespace.get(module.definition, None)

            if node_cls is None:
                for base_class in inspect.getmro(module.__class__):
                    if base_class.__name__ in self.namespace:
                        node_cls = self.namespace[base_class.__name__]
                        break

        if node_cls:
            svgen_inst = node_cls(module, parent=self.cur_hier)
            self.svgen_map[module] = svgen_inst
        else:
            svgen_inst = None

        if self.cur_hier is None:
            self.design = svgen_inst

        return svgen_inst

    def Gear(self, module):
        inst = self.instantiate(module)

        if inst:
            self.cur_hier = inst
            super().HierNode(module)
            self.cur_hier = self.cur_hier.parent

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
        }
        cls.registry['RTLNodeMap'] = {}

    @classmethod
    def reset(cls):
        cls.registry['RTLNodeMap'] = {}
