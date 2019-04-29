from pygears import registry, safe_bind
from pygears.core.hier_node import HierVisitorBase
from pygears.rtl.gear import RTLGear
import inspect
from pygears.core.gear import GearPlugin
from pygears.conf import inject, Inject


class RTLNodeInstVisitor(HierVisitorBase):
    @inject
    def __init__(self,
                 namespace=Inject('rtl/namespace/gear_gen'),
                 rtl_map=Inject('rtl/gear_node_map')):

        self.cur_hier = None
        self.design = None
        self.namespace = namespace
        self.rtl_map = rtl_map

    def Gear(self, module):
        if module in self.rtl_map:
            self.cur_hier.add_child(module)
            return True

        node = self.instantiate(module)
        self.rtl_map[module] = node

        if self.cur_hier is None:
            self.design = node

        if node:
            self.cur_hier = node
            super().HierNode(module)
            self.cur_hier = self.cur_hier.parent

        return True

    def GearHierRoot(self, module):
        self.design = self.instantiate(module)
        self.cur_hier = self.design
        self.rtl_map[module] = self.design

    def instantiate(self, module):
        svgen = module.params.get('svgen')

        if svgen is None:
            svgen = {}
            module.params['svgen'] = svgen

        if 'node_cls' in svgen:
            node_cls = svgen['node_cls']
        else:
            node_cls = self.namespace.get(module.definition, None)

            if node_cls is None:
                for base_class in inspect.getmro(module.__class__):
                    if base_class.__name__ in self.namespace:
                        node_cls = self.namespace[base_class.__name__]
                        break

        if not node_cls:
            return None

        node = node_cls(module, parent=self.cur_hier)

        for p in module.in_ports:
            node.add_in_port(p.basename, p.producer, p.consumer, p.dtype)

        for p in module.out_ports:
            node.add_out_port(p.basename, p.producer, p.consumer, p.dtype)

        return node


def rtl_inst(top, conf):
    v = RTLNodeInstVisitor()
    v.visit(top)

    return v.design


class RTLNodeInstPlugin(GearPlugin):
    @classmethod
    def bind(cls):
        safe_bind('rtl/namespace/gear_gen', {
            'Gear': RTLGear,
            'GearHierRoot': RTLGear
        })
        safe_bind('rtl/gear_node_map', {})
        registry('gear/params/extra')['svgen'] = None
