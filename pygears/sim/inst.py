from pygears import registry, safe_bind
from pygears.sim.sim_gear import SimGear, is_simgear_func
from pygears.sim.sim import SimPlugin
from pygears.core.gear import GearPlugin
from pygears.core.hier_node import HierVisitorBase


class SimInstVisitor(HierVisitorBase):
    def __init__(self):
        self.namespace = registry('sim/module_namespace')
        self.sim_map = registry('sim/map')

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
        # cls.registry['SimFlow'].append(sim_inst)
        cls.registry['sim']['flow'].append(sim_inst)
        safe_bind('sim/module_namespace', {})
        safe_bind('sim/map', {})
        safe_bind('gear/params/extra/sim_cls', None)

    @classmethod
    def reset(cls):
        cls.bind_val('sim/map', {})
