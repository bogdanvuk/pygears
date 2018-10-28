import asyncio
import itertools
import logging
import os
import random
import tempfile
import time

from pygears import GearDone, bind, find, registry, safe_bind
from pygears.conf import CustomLog, LogFmtFilter
from pygears.core.gear import GearPlugin
from pygears.core.intf import get_consumer_tree
from pygears.core.sim_event import SimEvent


def timestep():
    try:
        return registry('sim/timestep')
    except KeyError:
        return None


def sim_phase():
    return registry('sim/simulator').phase


def clk():
    registry('gear/current_module').phase = 'forward'
    return registry('sim/clk_event').wait()


async def delta():
    registry('gear/current_module').phase = 'back'
    await asyncio.sleep(0)
    return sim_phase()


def artifacts_dir():
    return registry('sim/artifact_dir')


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


def is_on_loopy_path(cur_path, g, consumer):
    if (g, consumer) in cur_path:
        return False

    for _, consumer in cur_path:
        if consumer == g:
            return True
    else:
        return False


# A recursive function used by topo_sort
def topo_sort_util(g, dag, visited, stack, cur_path):

    # print(f'{topo_sort_util.indent}Visiting: {g.name}')
    # Mark the current node as visited.
    visited.add(g)

    topo_sort_util.indent = topo_sort_util.indent + "    "
    # Recur for all the vertices adjacent to this vertex
    for consumer in dag[g]:
        # print(f'{topo_sort_util.indent}Adjasent: {consumer.name}')
        if ((consumer not in visited)
                or is_on_loopy_path(cur_path, g, consumer)):
            cur_path.append((g, consumer))
            topo_sort_util(consumer, dag, visited, stack, cur_path)
            cur_path.pop()

    topo_sort_util.indent = topo_sort_util.indent[:-4]
    # Push current vertex to stack which stores result
    # print(f'{topo_sort_util.indent}Stack: {g.name}')
    stack.insert(0, g)


topo_sort_util.indent = ""


def topo_sort(dag):
    # Mark all the vertices as not visited
    stack = []
    visited = set()
    cur_path = []

    # for i, g in enumerate(dag):
    #     if not g.in_ports:
    #         stack.append(g)
    #         visited[i] = True

    # Call the recursive helper function to store Topological
    # Sort starting from all vertices one by one
    for g in dag:
        if g not in visited:
            topo_sort_util(g, dag, visited, stack, cur_path)

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
            'after_finish': SimEvent(),
            'at_exit': SimEvent()
        }

    def get_debug(self):
        return False

    def get_tasks(self):
        self.sim_map = registry('sim/map')
        dag = {}

        for g in self.sim_map:
            dag[g] = []
            g.phase = 'forward'
            for p in g.out_ports:
                dag[g].extend(
                    [port.gear for port in get_consumer_tree(p.producer)])

        gear_order = topo_sort(dag)
        # print("-" * 60)
        # print("Topological order:")
        # for g in gear_order:
        #     print(g.name)

        # print("-" * 60)

        # raise

        self.sim_gears = [self.sim_map[g] for g in gear_order]
        self.tasks = {g: g.run() for g in set(self.sim_gears)}
        self.task_data = {g: None for g in set(self.sim_gears)}

    def call_soon(self, callback, fut):
        callback(fut)

    def future_done(self, fut):
        sim_gear, phase = self.wait_list.pop(fut)
        if fut.cancelled():
            # Interface that sim_gear waited on is done, so we need to finish
            # the sim_gear too
            self.schedule_to_finish(sim_gear)
        else:
            # If sim_gear was waiting for ack
            if phase == 'back':
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

    def run_gear(self, sim_gear, ready):

        # self.cur_gear.phase = 'forward'

        if ready is self.forward_ready:
            before_event = self.events['before_call_forward']
            after_event = self.events['after_call_forward']
        else:
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
                self.wait_list[data] = (sim_gear, self.cur_gear.phase)
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

        # print(f'{self.phase}: {sim_gear.gear.name}')
        self.run_gear(sim_gear, ready)

        self.cur_gear = registry('gear/hier_root')
        bind('gear/current_module', self.cur_gear)

    def sim_loop(self, timeout):
        clk = registry('sim/clk_event')
        delta = registry('sim/delta_event')
        timestep = 0

        start_time = time.time()

        sim_log().info("-------------- Simulation start --------------")
        while (self.forward_ready or self.back_ready or self.delta_ready
               or self._schedule_to_finish):
            self.phase = 'forward'
            for sim_gear in self.sim_gears:
                if ((sim_gear in self.forward_ready)
                        or (sim_gear in self.delta_ready)):
                    self.maybe_run_gear(sim_gear, self.forward_ready)

            self.phase = 'delta'
            delta.set()
            delta.clear()

            self.phase = 'back'

            for sim_gear in reversed(self.sim_gears):
                if sim_gear in self._schedule_to_finish:
                    self._finish(sim_gear)
                    self._schedule_to_finish.remove(sim_gear)

                if ((sim_gear in self.back_ready)
                        or (sim_gear in self.delta_ready)):
                    self.maybe_run_gear(sim_gear, self.back_ready)

            self.phase = 'cycle'

            self.events['before_timestep'](self, timestep)

            clk.set()
            clk.clear()
            timestep += 1
            bind('sim/timestep', timestep)

            # if (timestep % 1000) == 0:
            #     sim_log().info("-------------- Simulation cycle --------------")

            # print(f"-------------- {timestep} ------------------")

            self.events['after_timestep'](self, timestep)
            if (timeout is not None) and (timestep == timeout):
                break

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
        bind('sim/timestep', 0)

        self.events['before_setup'](self)

        for sim_gear in set(self.sim_gears):
            self.cur_gear = sim_gear.gear
            bind('gear/current_module', self.cur_gear)
            sim_gear.setup()
            self.cur_gear = registry('gear/hier_root')
            bind('gear/current_module', self.cur_gear)

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
                    self._finish(sim_gear)

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
    bind('sim/artifact_dir', outdir)

    if not seed:
        seed = int(time.time())
    random.seed(seed)
    bind('sim/rand_seed', seed)
    sim_log().info(f'Running sim with seed: {seed}')

    loop = EventLoop()
    asyncio.set_event_loop(loop)
    bind('sim/simulator', loop)

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
        bind('logger/sim/error/exception', True)
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
        safe_bind('gear/params/extra/sim_setup', None)
        SimLog('sim')

    @classmethod
    def reset(cls):
        safe_bind('sim/tasks', {})


def sim_assert(cond, msg=None):
    if not cond:
        sim_log().error(f'Assertion failed: {msg}')
