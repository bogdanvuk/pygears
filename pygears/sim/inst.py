import inspect
import asyncio
from pygears import registry, PluginBase, Intf
from pygears.core.hier_node import HierVisitorBase
from pygears.sim.verilate import SimVerilated
from pygears.sim.sim_gear import SimGear, is_simgear_func

def sim_inst(top, conf):

    namespace = registry('SimModuleNamespace')
    sim_map = registry('SimMap')
    outdir = conf['outdir']

    for gear in top.child:
        sim_cls = namespace.get(gear.definition, None)

        if sim_cls:
            sim_inst = sim_cls(gear)
        elif is_simgear_func(gear.func):
            sim_inst = SimGear(gear)
        else:
            sim_inst = SimVerilated(gear, outdir)

        if sim_inst:
            sim_map[gear] = sim_inst


class SimInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SimModuleNamespace'] = {}
        cls.registry['SimMap'] = {}

    @classmethod
    def reset(cls):
        cls.registry['SimMap'] = {}
