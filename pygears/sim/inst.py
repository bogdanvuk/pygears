import inspect

from pygears import registry, safe_bind, Intf, bind
from pygears.sim.sim_gear import SimGear, is_simgear_func
from pygears.sim.sim import SimPlugin
from pygears.core.gear import GearPlugin
from pygears.core.gear_inst import gear_base_resolver
from pygears.core.hier_node import HierVisitorBase
from pygears.core.port import HDLConsumer, HDLProducer


def sim_compile_resolver(func, meta_kwds, *args, **kwds):
    ctx = registry('gear/exec_context')
    if ctx == 'sim':
        safe_bind('gear/exec_context', 'compile')
        local_in = []
        for a in args:
            if isinstance(a, Intf):
                local_in.append(a)
            else:
                from pygears.lib.const import get_literal_type
                local_in.append(Intf(get_literal_type(a)))

        safe_bind('gear/exec_context', 'sim')

        outputs = gear_base_resolver(func, meta_kwds, *local_in, **kwds)

        # TODO: Support multiple outputs

        # outputs.connect(HDLConsumer())

        if isinstance(outputs, tuple):
            raise Exception("Not yet supported")

        gear_inst = outputs.producer.gear

        def is_async_gen(func):
            return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)

        if not is_async_gen(gear_inst.func):
            raise Exception("Not yet supported")

        import asyncio
        for intf, a in zip(local_in, args):
            if isinstance(a, Intf):
                continue

            intf._in_queue = asyncio.Queue(maxsize=1,
                                           loop=registry('sim/simulator'))
            intf.put_nb(a)

        simulator = registry('sim/simulator')
        cur_sim = registry('gear/current_sim')
        sim_gear = SimGear(gear_inst)
        sim_map = registry('sim/map')
        sim_map[gear_inst] = sim_gear
        simulator.insert_gears([gear_inst], simulator.cur_task_id)
        simulator.forward_ready.add(sim_gear)
        # sim_gear.setup()
        # simulator.sim_gears.insert(simulator.cur_task_id, sim_gear)
        simulator.sim_gears.insert(simulator.cur_task_id + 1, cur_sim)
        # simulator.tasks[sim_gear] = sim_gear.run()
        # simulator.task_data[sim_gear] = None

        return outputs

        # return gear_inst.func(*(p.consumer for p in gear_inst.in_ports),
        #                       **gear_inst.explicit_params)
    else:
        return gear_base_resolver(func, meta_kwds, *args, **kwds)


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
            sim_inst = sim_cls(module)
        elif is_simgear_func(module.func):
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
        cls.registry['sim']['flow'].append(sim_inst)
        safe_bind('sim/module_namespace', {})
        safe_bind('sim/map', {})
        safe_bind('gear/params/extra/sim_cls', None)
        bind('gear/gear_dflt_resolver', sim_compile_resolver)

    @classmethod
    def reset(cls):
        cls.bind_val('sim/map', {})
