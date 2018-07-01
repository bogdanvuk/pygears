import asyncio
from concurrent.futures import Future
import tempfile
import os
import itertools

from pygears import registry, find, PluginBase, bind, GearDone
from pygears.sim.inst import sim_inst
from pygears.core.intf import get_consumer_tree
from pygears.core.sim_event import SimEvent
from pygears.core.gear import GearPlugin

def cur_gear():
    loop = asyncio.get_event_loop()
    return loop.cur_gear


def artifacts_dir():
    return registry('SimArtifactDir')


class SimFuture(Future):
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
            'before_timestep': SimEvent(),
            'after_timestep': SimEvent(),
            'after_cleanup': SimEvent()
        }

    def get_tasks(self):
        self.sim_map = registry('SimMap')
        dag = {}

        for g in self.sim_map:
            dag[g] = []
            for p in g.out_ports:
                dag[g].extend(
                    [port.gear for port in get_consumer_tree(p.producer)])

        gear_order = topo_sort(dag)
        self.sim_gears = [self.sim_map[g] for g in gear_order]
        self.tasks = {g: g.run() for g in self.sim_gears}
        self.task_data = {g: None for g in self.sim_gears}

    def fut_done(self, fut):
        sim_gear = self.wait_list.pop(fut)
        if fut.cancelled():
            self.cancelled.add(sim_gear)
            print(f'Future cancelled: {sim_gear.gear.name} ready.')
        else:
            self.ready.add(sim_gear)
            print(f'Future done: {sim_gear.gear.name} ready.')

    def create_future(self):
        """Create a Future object attached to the loop."""
        fut = SimFuture()
        fut.add_done_callback(self.fut_done)

        return fut

    def cancel(self, sim_gear):
        try:
            self.tasks[sim_gear].throw(GearDone)
        except (StopIteration, GearDone):
            self.done.add(sim_gear)
        else:
            raise Exception("Gear didn't stop on cancel!")


    def maybe_run_gear(self, sim_gear):
        if sim_gear in self.cancelled:
            self.cancel(sim_gear)
            self.cancelled.remove(sim_gear)

        if sim_gear not in self.ready:
            return

        self.ready.remove(sim_gear)

        self.cur_gear = sim_gear.gear
        bind('CurrentModule', self.cur_gear)
        print(f"Running task {sim_gear.gear.name}")
        try:
            data = self.tasks[sim_gear].send(self.task_data[sim_gear])
        except (StopIteration, GearDone):
            self.done.add(sim_gear)
            print(f"Task {sim_gear.gear.name} done")
        else:
            if isinstance(data, SimFuture):
                self.wait_list[data] = sim_gear

            self.task_data[sim_gear] = data

    def run(self, timeout=None):
        self.get_tasks()
        self.wait_list = {}
        self.ready = set(self.sim_gears)
        self.cancelled = set()
        self.done = set()
        bind('ClkEvent', asyncio.Event())
        bind('DeltaEvent', asyncio.Event())
        bind('Timestep', 0)

        clk = registry('ClkEvent')
        delta = registry('DeltaEvent')
        timestep = 0

        self.events['before_setup'](self)

        for sim_gear in self.sim_gears:
            sim_gear.setup()

        self.events['before_run'](self)
        while self.ready:
            print("Forward pass...")
            for sim_gear in self.sim_gears:
                self.maybe_run_gear(sim_gear)

            delta.set()
            delta.clear()

            print("Back pass...")
            for sim_gear in reversed(self.sim_gears):
                self.maybe_run_gear(sim_gear)

            self.events['before_timestep'](self, timestep)

            clk.set()
            clk.clear()
            timestep += 1
            print(f"-------------- {timestep} ------------------")
            bind('Timestep', timestep)

            self.events['after_timestep'](self, timestep)
            if (timeout is not None) and (timestep == timeout):
                break

        print(f"----------- Simulation done ---------------")

        self.events['after_run'](self)

        for sim_gear in self.sim_gears:
            if not sim_gear in self.done:
                # print(f'Canceling {sim_gear.gear.name}')
                self.cancel(sim_gear)

        self.events['after_cleanup'](self)


def sim(outdir=None, extens=[], run=True, **conf):
    if outdir is None:
        outdir = tempfile.mkdtemp()

    conf["outdir"] = outdir
    os.makedirs(conf['outdir'], exist_ok=True)

    bind('SimArtifactDir', conf['outdir'])

    loop = EventLoop()
    asyncio.set_event_loop(loop)
    bind('Simulator', loop)

    top = find('/')
    for oper in itertools.chain(registry('SimFlow'), extens):
        top = oper(top, conf)

    if run:
        loop.run()

    return loop


class SimPlugin(GearPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'] = [sim_inst]
        cls.registry['SimTasks'] = {}
        cls.registry['SimConfig'] = {'dbg_assert': False}
        cls.registry['SVGenSystemVerilogImportPaths'] = []
        cls.registry['GearExtraParams']['sim_setup'] = None

    @classmethod
    def reset(cls):
        bind('SimTasks', {})


def sim_assert(cond, msg=None):
    if not cond:
        print(f'Assertion failed: {msg}')
        if registry('SimConfig')['dbg_assert']:
            import pdb
            pdb.set_trace()
        else:
            assert cond
