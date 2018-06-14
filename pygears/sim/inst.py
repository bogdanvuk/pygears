import inspect
import asyncio
from pygears import registry, PluginBase, Intf
from pygears.core.hier_node import HierVisitorBase
from pygears.sim.verilate import SimVerilated
from pygears.sim.sim_gear import SimGear, is_simgear_func
from pygears.core.gear import GearPlugin

def sim_inst(top, conf):

    namespace = registry('SimModuleNamespace')
    sim_map = registry('SimMap')
    outdir = conf['outdir']

    for gear in top.child:
        sim_cls = gear.params.get('sim_cls', None)

        if sim_cls is None:
            sim_cls = namespace.get(gear.definition, None)

        # if sim_cls is None:
        #     for base_class in inspect.getmro(gear.__class__):
        #         if base_class.__name__ in namespace:
        #             print(base_class.__name__)
        #             node_cls = namespace[base_class.__name__]
        #             break

        if sim_cls:
            sim_inst = sim_cls(gear)
        elif is_simgear_func(gear.func):
            sim_inst = SimGear(gear)
        # else:
        #     sim_inst = SimVerilated(gear, outdir)

        if sim_inst:
            sim_map[gear] = sim_inst


class SimInstPlugin(GearPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SimModuleNamespace'] = {}
        cls.registry['SimMap'] = {}
        print("Here")
        cls.registry['GearExtraParams']['sim_cls'] = None

    @classmethod
    def reset(cls):
        cls.registry['SimMap'] = {}
