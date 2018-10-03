import asyncio
import itertools
import logging
import os
import random
import sys
import tempfile
import time

from pygears import GearDone, bind, find, registry
from pygears.core.gear import GearPlugin
from pygears.core.intf import get_consumer_tree
from pygears.core.log import CustomLog, LogFmtFilter
from pygears.core.sim_event import SimEvent


def timestep():
    try:
        return registry('Timestep')
    except KeyError:
        return None


def sim_phase():
    return registry('Simulator').phase


def clk():
    registry('CurrentModule').phase = 'forward'
    return registry('ClkEvent').wait()


def delta():
    registry('CurrentModule').phase = 'back'
    return registry('DeltaEvent').wait()


def artifacts_dir():
    return registry('SimArtifactDir')


def cancel(gear):
    sim = registry('Simulator')
    sim.cancelled.add(registry('SimMap')[gear])


class SimFuture(asyncio.Future):
    # def _schedule_callbacks(self):
    #     self._loop.fut_done(self)

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
            'after_cancel': SimEvent(),
            'at_exit': SimEvent()
        }

    def get_debug(self):
        return False

    def get_tasks(self):
        self.sim_map = registry('SimMap')
        dag = {}

        for g in self.sim_map:
            dag[g] = []
            for p in g.out_ports:
                dag[g].extend(
                    [port.gear for port in get_consumer_tree(p.producer)])

        gear_order = topo_sort(dag)
        # print("Topological order:")
        # for g in gear_order:
        #     print(g.name)

        # print("-"*60)

        self.sim_gears = [self.sim_map[g] for g in gear_order]
        self.tasks = {g: g.run() for g in self.sim_gears}
        self.task_data = {g: None for g in self.sim_gears}

    def call_soon(self, callback, fut):
        callback(fut)

    def fut_done(self, fut):
        sim_gear, join = self.wait_list.pop(fut)
        if fut.cancelled():
            self.cancelled.add(sim_gear)
            # print(f'Future cancelled: {sim_gear.gear.name} {join}.')
        else:
            if join:
                self.back_ready.add(sim_gear)
            else:
                self.forward_ready.add(sim_gear)

            # print(f'Future done: {sim_gear.gear.name} ready.')

    def create_future(self):
        """Create a Future object attached to the loop."""
        fut = SimFuture()
        fut.add_done_callback(self.fut_done)

        return fut

    def cancel(self, sim_gear):
        try:
            self.cur_gear = sim_gear.gear
            bind('CurrentModule', self.cur_gear)
            self.tasks[sim_gear].throw(GearDone)
        except (StopIteration, GearDone):
            pass
        else:
            sim_log().error("Gear didn't stop on cancel!")
        finally:
            self.done.add(sim_gear)
            self.events['after_cancel'](self, sim_gear)
            self.cur_gear = registry('HierRoot')
            self.back_ready.discard(sim_gear)
            self.forward_ready.discard(sim_gear)
            bind('CurrentModule', self.cur_gear)

    def run_gear(self, sim_gear, ready):
        try:
            self.cur_gear.phase = 'forward'

            if ready is self.forward_ready:
                ebef = self.events['before_call_forward']
            else:
                ebef = self.events['before_call_back']

            if ebef:
                ebef(self, sim_gear)

            data = self.tasks[sim_gear].send(self.task_data[sim_gear])

            if ready is self.forward_ready:
                eafter = self.events['after_call_forward']
            else:
                eafter = self.events['after_call_back']

            if eafter:
                eafter(self, sim_gear)
        except (StopIteration, GearDone):
            self.done.add(sim_gear)
        else:
            if isinstance(data, SimFuture):
                self.wait_list[data] = (sim_gear,
                                        self.cur_gear.phase == 'back')

            self.task_data[sim_gear] = data

    def maybe_run_gear(self, sim_gear, ready):
        if sim_gear not in ready:
            return

        ready.remove(sim_gear)

        self.cur_gear = sim_gear.gear
        bind('CurrentModule', self.cur_gear)

        self.run_gear(sim_gear, ready)

        self.cur_gear = registry('HierRoot')
        bind('CurrentModule', self.cur_gear)

    def sim_loop(self, timeout):
        clk = registry('ClkEvent')
        delta = registry('DeltaEvent')
        timestep = 0

        start_time = time.time()

        sim_log().info("-------------- Simulation start --------------")
        while self.forward_ready or self.back_ready or self.cancelled:
            self.phase = 'forward'
            for sim_gear in self.sim_gears:
                if sim_gear in self.forward_ready:
                    self.maybe_run_gear(sim_gear, self.forward_ready)

            self.phase = 'delta'
            delta.set()
            delta.clear()

            self.phase = 'back'

            for sim_gear in reversed(self.sim_gears):
                if sim_gear in self.cancelled:
                    self.cancel(sim_gear)
                    self.cancelled.remove(sim_gear)

                if sim_gear in self.back_ready:
                    self.maybe_run_gear(sim_gear, self.back_ready)

            self.phase = 'cycle'

            self.events['before_timestep'](self, timestep)

            clk.set()
            clk.clear()
            timestep += 1
            bind('Timestep', timestep)

            # if (timestep % 1000) == 0:
            #     sim_log().info("-------------- Simulation cycle --------------")

            # print(f"-------------- {timestep} ------------------")

            self.events['after_timestep'](self, timestep)
            if (timeout is not None) and (timestep == timeout):
                break

        sim_log().info(f"----------- Simulation done ---------------")
        sim_log().info(f'Elapsed: {time.time() - start_time:.2f}')

        # while self.cancelled:
        #     # print(f'Canceling {sim_gear.gear.name}')
        #     sim_gear = self.cancelled.pop()
        #     self.cancel(sim_gear)

    def run(self, timeout=None):
        self.get_tasks()
        self.wait_list = {}
        self.forward_ready = set(self.sim_gears)
        self.back_ready = set()
        self.cancelled = set()
        self.done = set()

        bind('ClkEvent', asyncio.Event())
        bind('DeltaEvent', asyncio.Event())
        bind('Timestep', 0)

        self.events['before_setup'](self)

        for sim_gear in self.sim_gears:
            self.cur_gear = sim_gear.gear
            bind('CurrentModule', self.cur_gear)
            sim_gear.setup()
            self.cur_gear = registry('HierRoot')
            bind('CurrentModule', self.cur_gear)

        self.events['before_run'](self)

        sim_exception = None
        try:
            self.sim_loop(timeout)
        except Exception as e:
            sim_exception = e

        # print(f"----------- After run ---------------")
        self.events['after_run'](self)

        if not sim_exception:
            for sim_gear in self.sim_gears:
                if sim_gear not in self.done:
                    # sim_log().debug(f"Canceling {sim_gear.gear.name}")
                    self.cancel(sim_gear)

        self.events['after_cleanup'](self)
        self.events['at_exit'](self)

        if sim_exception:
            raise sim_exception


def sim(outdir=None,
        timeout=None,
        extens=[],
        run=True,
        verbosity=logging.INFO,
        seed=None):

    if outdir is None:
        outdir = tempfile.mkdtemp()
    os.makedirs(outdir, exist_ok=True)
    bind('SimArtifactDir', outdir)

    if not seed:
        seed = int(time.time())
    random.seed(seed)
    bind('SimRandSeed', seed)
    sim_log().info(f'Running sim with seed: {seed}')

    loop = EventLoop()
    asyncio.set_event_loop(loop)
    bind('Simulator', loop)

    top = find('/')
    for oper in itertools.chain(registry('SimFlow'), extens):
        oper(top)

    if run:
        loop.run(timeout)

    return loop


class SimFmtFilter(LogFmtFilter):
    def filter(self, record):
        super().filter(record)

        m = registry('CurrentModule')

        record.module = m.name
        record.timestep = timestep()
        if record.timestep is None:
            record.timestep = '-'

        return True


class SimLog(CustomLog):
    def __init__(self, name, verbosity=logging.INFO):
        super().__init__(name, verbosity)

        # change default for error
        registry('simLog')['error']['exception'] = True
        registry('simLog')['print_traceback'] = False

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
        cls.registry['SimFlow'] = []
        cls.registry['SimTasks'] = {}
        cls.registry['SimConfig'] = {}
        cls.registry['GearExtraParams']['sim_setup'] = None
        SimLog('sim')

    @classmethod
    def reset(cls):
        bind('SimTasks', {})


def sim_assert(cond, msg=None):
    if not cond:
        sim_log().error(f'Assertion failed: {msg}')
