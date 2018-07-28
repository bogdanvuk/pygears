from pygears import registry
from pygears.sim.sim_gear import SimGear, is_simgear_func
from pygears.sim.sim import SimPlugin
from pygears.core.gear import GearPlugin
from pygears.core.hier_node import HierVisitorBase


class SimInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = registry('SimModuleNamespace')
        self.sim_map = registry('SimMap')

    def Gear(self, module):
        sim_cls = module.params.get('sim_cls', None)
        sim_inst = None

        if sim_cls is None:
            sim_cls = self.namespace.get(module.definition, None)

        if sim_cls:
            # print(f"Recognized {module.name} as {sim_cls}")
            sim_inst = sim_cls(module)
        elif is_simgear_func(module.func):
            # print(f"Recognized {module.name} as sim_gear")
            sim_inst = SimGear(module)

        if sim_inst:
            self.sim_map[module] = sim_inst
            return True


def sim_inst(top):
    v = SimInstVisitor()
    v.visit(top)

    return top


class SimInstPlugin(SimPlugin, GearPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'].append(sim_inst)
        cls.registry['SimModuleNamespace'] = {}
        cls.registry['SimMap'] = {}
        cls.registry['GearExtraParams']['sim_cls'] = None

    @classmethod
    def reset(cls):
        cls.registry['SimMap'] = {}
