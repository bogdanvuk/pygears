import asyncio
import itertools
import logging
import os
import random
import sys
import tempfile
import time

from pygears import GearDone, bind, find, registry, safe_bind
from pygears.conf import CustomLog, LogFmtFilter
from pygears.core.gear import GearPlugin, Gear
# from pygears.core.intf import get_consumer_tree as intf_get_consumer_tree
from pygears.core.port import InPort, OutPort
from pygears.core.sim_event import SimEvent
from pygears.core.hier_node import HierVisitorBase


class SimFinish(Exception):
    pass


def timestep():
    try:
        return registry('sim/timestep')
    except KeyError:
        return None


def sim_phase():
    return registry('sim/simulator').phase


def clk():
    registry('gear/current_sim').phase = 'forward'
    return registry('sim/clk_event').wait()


async def delta():
    registry('gear/current_sim').phase = 'back'
    await asyncio.sleep(0)
    return sim_phase()


def artifacts_dir():
    return registry('sim/artifacts_dir')


def schedule_to_finish(gear):
    sim = registry('sim/simulator')
    sim.schedule_to_finish(registry('sim/map')[gear])


class SimFuture(asyncio.Future):
    # def _schedule_callbacks(self):
    #     self._loop.future_done(self)

    def coro_iter(self):
        yield self

    def __iter__(self):
        return self.coro_iter()

    __await__ = __iter__


# A recursive function used by topo_sort
def topo_sort_util(v, g, dag, visited, stack):

    # Mark the current node as visited.
    visited[v] = True

    # Recur for all the vertices adjacent to this vertex
    for consumer in dag[g]:
        i = list(dag.keys()).index(consumer)
        if not visited[i]:
            topo_sort_util(i, consumer, dag, visited, stack)

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
            topo_sort_util(i, g, dag, visited, stack)

    return stack


def _get_consumer_tree_rec(root_intf, cur_intf, consumers):
    for port in cur_intf.consumers:
        cons_intf = port.consumer
        if port in registry('sim/map'):
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

    def get_tasks(self):
        self.sim_map = registry('sim/map')
        dag = {}

        # for g in self.sim_map:
        #     dag[g] = []
        #     g.phase = 'forward'
        #     for p in g.out_ports:
        #         dag[g].extend(
        #             [port.gear for port in get_consumer_tree(p.producer)])

        cosim_modules = [
            g for g in self.sim_map
            if isinstance(g, Gear) and g.params['sim_cls'] is not None
        ]

        v = GearEnum()
        v.visit(registry('gear/hier_root'))

        for g in v.gears:
            dag[g] = []
            for p in g.out_ports:
                dag[g].extend(get_consumer_tree(p.consumer))

        for g, sim_gear in self.sim_map.items():
            if isinstance(g, OutPort):
                if (not g.gear.hierarchical):
                    dag[g.gear].clear()

        for g, sim_gear in self.sim_map.items():
            if isinstance(g, InPort):
                if (not g.gear.hierarchical):
                    dag[g] = [g.gear]
                else:
                    dag[g] = get_consumer_tree(g.consumer)

            elif isinstance(g, OutPort):
                if (not g.gear.hierarchical):
                    dag[g.gear].append(g)

                dag[g] = get_consumer_tree(g.consumer)

        gear_order = topo_sort(dag)

        gear_multi_order = cosim_modules.copy()
        for g in gear_order:
            if (all(not m.is_descendent(g) for m in cosim_modules)
                    or isinstance(g, (InPort, OutPort))):
                gear_multi_order.append(g)

        # print("-" * 60)
        # print("Topological order:")
        # for g in gear_multi_order:
        #     print(f'{g.name}: {[c.name for c in dag.get(g, [])]}')

        # print("-" * 60)

        # raise

        for g in gear_multi_order:
            g.phase = 'forward'
            self.sim_map[g].phase = 'forward'

        self.sim_gears = [self.sim_map[g] for g in gear_multi_order]
        self.tasks = {g: g.run() for g in set(self.sim_gears)}
        self.task_data = {g: None for g in set(self.sim_gears)}

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
        try:
            self.cur_gear = sim_gear.gear
            bind('gear/current_module', self.cur_gear)
            bind('gear/current_sim', sim_gear)
            self.tasks[sim_gear].throw(GearDone)
        except (StopIteration, GearDone):
            pass
        else:
            sim_log().error("Gear didn't stop on finish!")
        finally:
            self.done.add(sim_gear)
            self.events['after_finish'](self, sim_gear)
            self.cur_gear = registry('gear/hier_root')
            self.back_ready.discard(sim_gear)
            self.forward_ready.discard(sim_gear)
            self.delta_ready.discard(sim_gear)
            bind('gear/current_module', self.cur_gear)
            bind('gear/current_sim', sim_gear)

    def run_gear(self, sim_gear, ready):

        # self.cur_gear.phase = 'forward'

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
        bind('gear/current_module', self.cur_gear)
        bind('gear/current_sim', sim_gear)

        # print(f'{self.phase}: {sim_gear.gear.name}')
        self.run_gear(sim_gear, ready)

        self.cur_gear = registry('gear/hier_root')
        bind('gear/current_module', self.cur_gear)
        bind('gear/current_sim', sim_gear)

    def sim_loop(self, timeout):
        clk = registry('sim/clk_event')
        delta = registry('sim/delta_event')

        bind('sim/timestep', 0)

        timestep = -1
        start_time = time.time()

        sim_log().info("-------------- Simulation start --------------")
        while (self.forward_ready or self.back_ready or self.delta_ready
               or self._schedule_to_finish):

            timestep += 1
            bind('sim/timestep', timestep)
            if (timeout is not None) and (timestep == timeout):
                break

            # if (timestep % 1000) == 0:
            #     sim_log().info("-------------- Simulation cycle --------------")

            # print(f"-------------- {timestep} ------------------")

            self.phase = 'forward'
            for sim_gear in self.sim_gears:
                if ((sim_gear in self.forward_ready)
                        or (sim_gear in self.delta_ready)):
                    # print(
                    #     f'Forward: {sim_gear.port.name if hasattr(sim_gear, "port") else sim_gear.gear.name}'
                    # )
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
                    # print(f'Clock: {sim_gear.gear.name}')
                    self.maybe_run_gear(sim_gear, self.delta_ready)

            self.events['after_timestep'](self, timestep)

        sim_log().info(f"----------- Simulation done ---------------")
        sim_log().info(f'Elapsed: {time.time() - start_time:.2f}')

        # while self.schedule_to_finish:
        #     # print(f'Canceling {sim_gear.gear.name}')
        #     sim_gear = self.schedule_to_finish.pop()
        #     self.finish(sim_gear)

    def run(self, timeout=None):
        self.get_tasks()
        self.wait_list = {}
        self.forward_ready = set(self.sim_gears)
        self.back_ready = set()
        self.delta_ready = set()
        self._schedule_to_finish = set()
        self.done = set()

        bind('sim/clk_event', asyncio.Event())
        bind('sim/delta_event', asyncio.Event())
        bind('sim/timestep', None)

        self.events['before_setup'](self)

        for sim_gear in set(self.sim_gears):
            self.cur_gear = sim_gear.gear
            bind('gear/current_module', self.cur_gear)
            bind('gear/current_sim', sim_gear)
            sim_gear.setup()
            self.cur_gear = registry('gear/hier_root')
            bind('gear/current_module', self.cur_gear)
            bind('gear/current_sim', sim_gear)

        sim_exception = None
        try:
            self.events['before_run'](self)
            self.sim_loop(timeout)
        except SimFinish:
            pass
        except Exception as e:
            sim_exception = e

        try:
            # print(f"----------- After run ---------------")

            if not sim_exception:
                self.events['after_run'](self)

                for sim_gear in self.sim_gears:
                    if sim_gear not in self.done:
                        self._finish(sim_gear)

            self.events['after_cleanup'](self)
            self.events['at_exit'](self)
        finally:
            if sim_exception:
                raise sim_exception


def sim(outdir=None,
        timeout=None,
        extens=None,
        run=True,
        verbosity=logging.INFO,
        check_activity=False,
        seed=None):

    if extens is None:
        extens = []

    if outdir is None:
        outdir = registry('sim/artifacts_dir')
        if outdir is None:
            outdir = tempfile.mkdtemp()

    bind('sim/artifacts_dir', outdir)
    os.makedirs(outdir, exist_ok=True)

    if not seed:
        seed = random.randrange(sys.maxsize)
    random.seed(seed)
    bind('sim/rand_seed', seed)

    sim_log().info(f'Running sim with seed: {seed}')

    loop = EventLoop()
    asyncio.set_event_loop(loop)
    bind('sim/simulator', loop)

    if check_activity:
        from pygears.sim.extens.activity import ActivityChecker
        if ActivityChecker not in extens:
            extens.append(ActivityChecker)

    top = find('/')
    for oper in itertools.chain(registry('sim/flow'), extens):
        oper(top)

    if run:
        loop.run(timeout)

    return loop


class SimFmtFilter(LogFmtFilter):
    def filter(self, record):
        super().filter(record)

        m = registry('gear/current_module')

        record.module = m.name
        record.timestep = timestep()
        if record.timestep is None:
            record.timestep = '-'

        return True


class SimLog(CustomLog):
    def __init__(self, name, verbosity=logging.INFO):
        super().__init__(name, verbosity)

        # change default for error
        bind('logger/sim/error', 'exception')
        bind('logger/sim/print_traceback', False)

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
        safe_bind('sim/config', {})
        safe_bind('sim/flow', [])
        safe_bind('sim/tasks', {})
        safe_bind('sim/artifacts_dir', None)
        safe_bind('gear/params/extra/sim_setup', None)
        SimLog('sim')

    @classmethod
    def reset(cls):
        safe_bind('sim/tasks', {})


def sim_assert(cond, msg=None):
    if not cond:
        sim_log().error(f'Assertion failed: {msg}')
