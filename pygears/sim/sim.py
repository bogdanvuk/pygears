import asyncio
import itertools
import logging
import os
import random
import sys
import tempfile
import time

from functools import partial
from pygears import GearDone, find, reg
from pygears.conf import CustomLogger, LogFmtFilter, register_custom_log
from pygears.core.gear import GearPlugin, Gear
# from pygears.core.intf import get_consumer_tree as intf_get_consumer_tree
from pygears.core.port import InPort, OutPort, HDLConsumer, HDLProducer
from pygears.core.sim_event import SimEvent
from pygears.core.hier_node import HierVisitorBase

gear_reg = {}
sim_reg = {}


class SimFinish(Exception):
    pass


class SimCyclic(Exception):
    pass


def timestep():
    try:
        return sim_reg['timestep']
    except KeyError:
        return None


def sim_phase():
    return sim_reg['simulator'].phase


def clk():
    # TODO: await clk() after yield (in back phase) might not have desired effect
    gear_reg['current_sim'].phase = 'forward'
    return sim_reg['clk_event'].wait()


async def delta():
    gear_reg['current_sim'].phase = 'back'
    await asyncio.sleep(0)
    return sim_reg['simulator'].phase


def artifacts_dir():
    return reg['results-dir']


def schedule_to_finish(gear):
    sim = sim_reg['simulator']
    sim.schedule_to_finish(sim_reg['map'][gear])


class SimFuture(asyncio.Future):
    def coro_iter(self):
        yield self

    def __iter__(self):
        return self.coro_iter()

    __await__ = __iter__


# A recursive function used by topo_sort
def topo_sort_util(v, g, dag, visited, stack, cycle):

    # Mark the current node as visited.
    visited[v] = True
    cycle.append(g)

    # Recur for all the vertices adjacent to this vertex
    for consumer in dag[g]:
        i = list(dag.keys()).index(consumer)
        if consumer in cycle:
            index = cycle.index(consumer)
            cycle.append(consumer)
            raise SimCyclic('Simulation not possible, gear cycle found:'
                            f' {" -> ".join([c.name for c in cycle[index:]])}')

        if not visited[i]:
            topo_sort_util(i, consumer, dag, visited, stack, cycle)

    cycle.pop()

    # Push current vertex to stack which stores result
    stack.insert(0, g)


def topo_sort(dag):
    # Mark all the vertices as not visited
    visited = [False] * len(dag)
    stack = []

    # for i, g in enumerate(dag):
    #     if not g.in_ports:
    #         stack.append(g)
    #         visited[i] = True

    # Call the recursive helper function to store Topological
    # Sort starting from all vertices one by one
    for i, g in enumerate(dag):
        if not visited[i]:
            topo_sort_util(i, g, dag, visited, stack, [])

    return stack


def _get_consumer_tree_rec(root_intf, cur_intf, consumers):
    for port in cur_intf.consumers:
        if isinstance(port, HDLConsumer):
            continue

        cons_intf = port.consumer
        if port in reg['sim/map']:
            consumers.append(port)
        elif port.gear.hierarchical:
            _get_consumer_tree_rec(root_intf, cons_intf, consumers)
        else:
            consumers.append(port.gear)


def get_consumer_tree(intf):
    consumers = []
    _get_consumer_tree_rec(intf, intf, consumers)
    return consumers


class GearEnum(HierVisitorBase):
    def __init__(self):
        self.gears = []

    def Gear(self, node):
        if not node.hierarchical:
            self.gears.append(node)


def cosim(top, sim, *args, **kwds):
    if top is None:
        top = reg['gear/root']
    elif isinstance(top, str):
        top_name = top
        top = find(top)

        if top is None:
            raise Exception(f'No gear found on path: "{top_name}"')

    if isinstance(sim, str):
        if sim in ['cadence', 'xsim', 'questa']:
            from .modules import SimSocket
            sim_cls = SimSocket
            kwds['sim'] = sim
        elif sim == 'verilator':
            from .modules import SimVerilated
            from .modules.verilator import build

            kwds['outdir'] = kwds.get('outdir', reg['results-dir'])
            kwds['rebuild'] = kwds.get('rebuild', True)
            sim_cls = SimVerilated
            build(top, **kwds)
            kwds['rebuild'] = False
        else:
            raise Exception(f"Unsupported simulator: {sim}")
    else:
        sim_cls = sim

    if args or kwds:
        top.params['sim_cls'] = partial(sim_cls, *args, **kwds)
    else:
        top.params['sim_cls'] = sim_cls


def simgear_exec_order(gears):
    sim_map = reg['sim/map']
    dag = {}

    for g in gears:
        dag[g] = []
        for p in g.out_ports:
            dag[g].extend(get_consumer_tree(p.consumer))

    for g, sim_gear in sim_map.items():
        if isinstance(g, OutPort):
            if (not g.gear.hierarchical):
                dag[g.gear].clear()

    for g, sim_gear in sim_map.items():
        if isinstance(g, InPort):
            #TODO: Following doesn't work when verilator adds InputPorts for channeled intfs
            # if (len(g.consumer.consumers) == 1
            #         and isinstance(g.consumer.consumers[0], HDLConsumer)):

            if (not g.gear.hierarchical):
                dag[g] = [g.gear]
            else:
                dag[g] = get_consumer_tree(g.consumer)

        elif isinstance(g, OutPort):
            #TODO: Test if this works
            # if isinstance(g.producer.producer, HDLProducer):
            if (not g.gear.hierarchical):
                dag[g.gear].append(g)

            dag[g] = get_consumer_tree(g.consumer)

    gear_order = topo_sort(dag)

    cosim_modules = [
        g for g in sim_map
        if isinstance(g, Gear) and g.params['sim_cls'] is not None
    ]

    gear_multi_order = cosim_modules.copy()
    for g in gear_order:
        if (all(not m.has_descendent(g) for m in cosim_modules)
                or isinstance(g, (InPort, OutPort))):
            gear_multi_order.append(g)

    # print('Order: ')
    # for g in gear_multi_order:
    #     print(g.name)

    # import networkx as nx
    # import matplotlib.pyplot as plt

    # G = nx.DiGraph()
    # for g in dag:
    #     for c in dag[g]:
    #         G.add_edge(g.name, c.name)

    # pos = nx.spring_layout(G)
    # nx.draw(G, pos, font_size=16, with_labels=False)

    # for p in pos:  # raise text positions
    #     pos[p][1] += 0.07

    # nx.draw_networkx_labels(G, pos)
    # plt.show()

    return gear_multi_order


class EventLoop(asyncio.events.AbstractEventLoop):
    def __init__(self):
        self.events = {
            'before_setup': SimEvent(),
            'before_run': SimEvent(),
            'after_run': SimEvent(),
            'before_call_forward': SimEvent(),
            'after_call_forward': SimEvent(),
            'before_call_back': SimEvent(),
            'after_call_back': SimEvent(),
            'before_timestep': SimEvent(),
            'after_timestep': SimEvent(),
            'after_cleanup': SimEvent(),
            'after_finish': SimEvent(),
            'at_exit': SimEvent()
        }

    def get_debug(self):
        return False

    def insert_gears(self, gears, pos=None):
        for g in gears:
            g.phase = 'forward'
            if g not in self.sim_map:
                raise Exception(
                    f'Gear "{g.name}" of type "{g.definition.__name__}" has'
                    f' no simulation model')

            self.sim_map[g].phase = 'forward'

        sim_gears = [self.sim_map[g] for g in gears]

        if pos is None:
            index = 0
        elif isinstance(pos, int):
            index = pos
        else:
            index = self.sim_gears.index(self.sim_map[pos])

        self.sim_gears[index:index] = sim_gears

        for g in set(sim_gears):
            self.tasks[g] = g.run()
            self.task_data[g] = None

    def call_soon(self, callback, *fut, context=None):
        callback(fut[0])

    def future_done(self, fut):
        sim_gear = self.wait_list.pop(fut)
        if fut.cancelled():
            # Interface that sim_gear waited on is done, so we need to finish
            # the sim_gear too
            self.schedule_to_finish(sim_gear)
        else:
            # If sim_gear was waiting for ack
            if sim_gear.phase == 'back':
                self.back_ready.add(sim_gear)
            else:
                self.forward_ready.add(sim_gear)

    def create_future(self):
        """Create a Future object attached to the loop."""
        fut = SimFuture()
        fut.add_done_callback(self.future_done)

        return fut

    def schedule_to_finish(self, sim_gear):
        '''Schedule module to be finished during next back phase.'''
        self._schedule_to_finish.add(sim_gear)

    def _finish(self, sim_gear):
        if sim_gear.done:
            return

        try:
            self.cur_gear = sim_gear.gear
            reg['gear/current_module'] = self.cur_gear
            reg['gear/current_sim'] = sim_gear
            self.tasks[sim_gear].throw(GearDone)
        except (StopIteration, GearDone):
            pass
        else:
            sim_log().error("Gear didn't stop on finish!")
        finally:
            self.done.add(sim_gear)
            self.events['after_finish'](self, sim_gear)
            self.cur_gear = reg['gear/root']
            self.back_ready.discard(sim_gear)
            self.forward_ready.discard(sim_gear)
            self.delta_ready.discard(sim_gear)
            reg['gear/current_module'] = self.cur_gear
            reg['gear/current_sim'] = sim_gear

    def run_gear(self, sim_gear, ready):
        before_event = None
        after_event = None

        if ready is self.forward_ready:
            before_event = self.events['before_call_forward']
            after_event = self.events['after_call_forward']
        elif ready is self.back_ready:
            before_event = self.events['before_call_back']
            after_event = self.events['after_call_back']

        if before_event:
            before_event(self, sim_gear)

        try:
            data = self.tasks[sim_gear].send(self.task_data[sim_gear])
        except (StopIteration, GearDone):
            self.done.add(sim_gear)
        else:
            if isinstance(data, SimFuture):
                self.wait_list[data] = sim_gear
            else:
                self.delta_ready.add(sim_gear)

            self.task_data[sim_gear] = data
        finally:
            if after_event:
                after_event(self, sim_gear)

    def maybe_run_gear(self, sim_gear, ready):
        ready.discard(sim_gear)
        self.delta_ready.discard(sim_gear)

        self.cur_gear = sim_gear.gear
        gear_reg['current_module'] = self.cur_gear
        gear_reg['current_sim'] = sim_gear

        # print(f'{self.phase}: {sim_gear.gear.name}')
        self.run_gear(sim_gear, ready)

        self.cur_gear = gear_reg['root']
        gear_reg['current_module'] = self.cur_gear
        gear_reg['current_sim'] = sim_gear

    def sim_loop(self, timeout):
        clk = reg['sim/clk_event']
        delta = reg['sim/delta_event']

        global gear_reg, sim_reg
        gear_reg = reg['gear']
        sim_reg = reg['sim']

        reg['sim/timestep'] = 0

        timestep = -1
        start_time = time.time()

        sim_log().info("-------------- Simulation start --------------")
        while (self.forward_ready or self.back_ready or self.delta_ready
               or self._schedule_to_finish):

            timestep += 1
            reg['sim/timestep'] = timestep
            if (timeout is not None) and (timestep == timeout):
                break

            # if (timestep % 1000) == 0:
            #     sim_log().info("-------------- Simulation cycle --------------")

            # print(f"-------------- {timestep} ------------------")

            self.phase = 'forward'
            i = 0
            while i < len(self.sim_gears):
                sim_gear = self.sim_gears[i]
                i += 1

                if ((sim_gear not in self.forward_ready)
                        and (sim_gear not in self.delta_ready)):
                    continue

                # print(
                #     f'Forward: {sim_gear.port.name if hasattr(sim_gear, "port") else sim_gear.gear.name}'
                # )
                self.cur_task_id = i
                self.maybe_run_gear(sim_gear, self.forward_ready)

            self.phase = 'delta'
            delta.set()
            delta.clear()

            self.phase = 'back'

            while self._schedule_to_finish:
                for sim_gear in self._schedule_to_finish.copy():
                    self._finish(sim_gear)
                    self._schedule_to_finish.remove(sim_gear)

            for sim_gear in reversed(self.sim_gears):
                if ((sim_gear in self.back_ready)
                        or (sim_gear in self.delta_ready)):
                    # print(
                    #     f'Back: {sim_gear.port.name if hasattr(sim_gear, "port") else sim_gear.gear.name}'
                    # )
                    self.maybe_run_gear(sim_gear, self.back_ready)

            self.phase = 'cycle'

            self.events['before_timestep'](self, timestep)

            clk.set()
            clk.clear()

            for sim_gear in reversed(self.sim_gears):
                if sim_gear in self.delta_ready:
                    # if hasattr(sim_gear, 'port'):
                    #     print(f'Clock: {sim_gear.gear.name}.{sim_gear.port.basename}')
                    # else:
                    #     print(f'Clock: {sim_gear.gear.name}')

                    self.maybe_run_gear(sim_gear, self.delta_ready)

            self.events['after_timestep'](self, timestep)

        sim_log().info(f"----------- Simulation done ---------------")
        sim_log().info(f'Elapsed: {time.time() - start_time:.2f}')

        # while self.schedule_to_finish:
        #     # print(f'Canceling {sim_gear.gear.name}')
        #     sim_gear = self.schedule_to_finish.pop()
        #     self.finish(sim_gear)

    def run(self, timeout=None):
        self.sim_map = reg['sim/map']
        self.sim_gears = []
        self.tasks = {}
        self.task_data = {}

        v = GearEnum()
        v.visit(reg['gear/root'])

        self.insert_gears(simgear_exec_order(v.gears))

        self.wait_list = {}
        self.forward_ready = set(self.sim_gears)
        self.back_ready = set()
        self.delta_ready = set()
        self._schedule_to_finish = set()
        self.done = set()

        reg['sim/clk_event'] = asyncio.Event()
        reg['sim/delta_event'] = asyncio.Event()
        reg['sim/timestep'] = None

        self.events['before_setup'](self)

        for sim_gear in set(self.sim_gears):
            self.cur_gear = sim_gear.gear
            reg['gear/current_module'] = self.cur_gear
            reg['gear/current_sim'] = sim_gear
            sim_gear.setup()
            self.cur_gear = reg['gear/root']
            reg['gear/current_module'] = self.cur_gear
            reg['gear/current_sim'] = sim_gear

        reg['sim/exception'] = None
        reg['gear/exec_context'] = 'sim'
        try:
            self.events['before_run'](self)
            self.sim_loop(timeout)
        except SimFinish:
            pass
        except Exception as e:
            reg['sim/exception'] = e

        reg['gear/exec_context'] = 'compile'

        try:
            # print(f"----------- After run ---------------")

            if not reg['sim/exception']:
                self.events['after_run'](self)

                for sim_gear in self.sim_gears:
                    if sim_gear not in self.done:
                        self._finish(sim_gear)

            self.events['after_cleanup'](self)
            self.events['at_exit'](self)
        finally:
            if reg['sim/exception']:
                raise reg['sim/exception']


def sim(resdir=None,
        timeout=None,
        extens=None,
        run=True,
        check_activity=False,
        seed=None):
    if reg['sim/dryrun']:
        return

    if extens is None:
        extens = []

    extens.extend(reg['sim/extens'])

    if resdir is None:
        resdir = reg['results-dir']

    reg['results-dir'] = resdir
    os.makedirs(resdir, exist_ok=True)

    if seed is None and reg['sim/rand_seed'] is None:
        seed = random.randrange(sys.maxsize)
        reg['sim/rand_seed'] = seed

    random.seed(reg['sim/rand_seed'])

    sim_log().info(f'Running sim with seed: {reg["sim/rand_seed"]}')

    loop = EventLoop()
    asyncio.set_event_loop(loop)
    reg['sim/simulator'] = loop

    if check_activity:
        from pygears.sim.extens.activity import ActivityChecker
        if ActivityChecker not in extens:
            extens.append(ActivityChecker)

    for oper in itertools.chain(reg['sim/flow'], extens):
        oper()

    if run:
        loop.run(timeout)

    return loop


class SimFmtFilter(LogFmtFilter):
    def filter(self, record):
        super().filter(record)

        m = reg['gear/current_module']

        record.module = m.name
        record.timestep = timestep()
        if record.timestep is None:
            record.timestep = '-'

        return True


class SimLog(CustomLogger):
    def get_format(self):
        return logging.Formatter(
            '%(timestep)s %(module)20s [%(levelname)s]: %(message)s %(err_file)s %(stack_file)s'
        )

    def get_filter(self):
        return SimFmtFilter()


def sim_log():
    return logging.getLogger('sim')


class SimPlugin(GearPlugin):
    @classmethod
    def bind(cls):
        global gear_reg, sim_reg
        gear_reg = {}
        sim_reg = {}

        reg['sim/config'] = {}
        reg['sim/flow'] = []
        reg['sim/tasks'] = {}
        reg['sim/simulator'] = None
        reg['sim/dryrun'] = False
        reg.confdef('sim/rand_seed', None)
        reg.confdef('sim/clk_freq', 1000)
        reg.confdef('results-dir', default=tempfile.mkdtemp())
        reg.confdef('sim/extens', default=[])

        reg['gear/params/extra/sim_setup'] = None
        register_custom_log('sim', cls=SimLog)

        # temporary hack for pytest logger reset issue
        reg['logger/sim/error'] = 'exception'
        reg['logger/sim/print_traceback'] = False

    @classmethod
    def reset(cls):
        reg['sim/tasks'] = {}


def sim_assert(cond, msg=None):
    if not cond:
        sim_log().error(f'Assertion failed: {msg}')
