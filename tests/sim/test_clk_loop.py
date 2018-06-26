from pygears import gear, find, bind, registry
from pygears.typing import Uint
from pygears.sim import seqr, drv, delta, clk
from pygears.cookbook.verif import check
from pygears.core.intf import get_consumer_tree

from types import coroutine

# @coroutine
# def nice():
#     yield

# async def hello(name):
#     print('Hello, %s!' % (name, ))
#     await nice()


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


from asyncio import events  #, tasks, futures
from concurrent.futures import Future
from types import coroutine


class SimFuture(Future):
    def coro_iter(self):
        yield self

    def __iter__(self):
        return self.coro_iter()

    __await__ = __iter__


class EventLoop(events.AbstractEventLoop):
    def fut_done(self, fut):
        print("Future done")

    def create_future(self):
        """Create a Future object attached to the loop."""
        fut = SimFuture()
        fut.add_done_callback(self.fut_done)

        return fut


#     def create_task(self, coro):
#         """Schedule a coroutine object.
#         Return a task object.
#         """
#         return tasks.Task(coro, loop=self)

#     def get_debug(self):
#         return False

#     def set_debug(self, enabled):
#         ...

#     def call_at(self, when, callback, *args, context=None):
#         """Like call_later(), but uses an absolute time.
#         Absolute time corresponds to the event loop's time() method.
#         """
#         self._check_closed()
#         if self._debug:
#             self._check_thread()
#             self._check_callback(callback, 'call_at')
#         timer = events.TimerHandle(when, callback, args, self, context)
#         if timer._source_traceback:
#             del timer._source_traceback[-1]
#         heapq.heappush(self._scheduled, timer)
#         timer._scheduled = True
#         return timer

#     def call_later(self, delay, callback, *args, context=None):
#         """Arrange for a callback to be called at a given time.
#         Return a Handle: an opaque object with a cancel() method that
#         can be used to cancel the call.
#         The delay can be an int or float, expressed in seconds.  It is
#         always relative to the current time.
#         Each callback will be called exactly once.  If two callbacks
#         are scheduled for exactly the same time, it undefined which
#         will be called first.
#         Any positional arguments after the callback will be passed to
#         the callback when it is called.
#         """
#         print(delay, callback, args, context)
#         # timer = self.call_at(self.time() + delay, callback, *args,
#         #                      context=context)
#         # if timer._source_traceback:
#         #     del timer._source_traceback[-1]
#         # return timer

#         raise NotImplementedError


def sim(**conf):

    top = find('/')
    for oper in registry('SimFlow'):
        top = oper(top, conf)

    sim_map = registry('SimMap')
    # tasks = {proc.run(): proc for proc in registry('SimMap').values()}
    dag = {}

    for g in sim_map:
        dag[g] = []
        for p in g.out_ports:
            dag[g].extend(
                [port.gear for port in get_consumer_tree(p.producer)])

    gear_order = topo_sort(dag)

    loop = EventLoop()
    bind('EventLoop', loop)

    tasks = {sim_map[g]: (sim_map[g].run(), None) for g in gear_order}

    while tasks:
        queue, tasks = tasks, {}
        for sim_gear, (task, data) in queue.items():
            # NEW: resume the task *once*.
            print(f"Running task {sim_gear.gear.name}")
            try:
                data = task.send(data)
            except StopIteration:
                pass
            # except Exception as error:
            #     # NEW: prevent crashed task from ending the loop.
            #     print(error)
            else:
                tasks[sim_gear] = (task, data)


def test_general():
    @gear
    async def priority_mux(*din: b'T') -> b'T':
        # await delta()

        for i, d in enumerate(din):
            if not d.empty():
                async with d as item:
                    print(f'Priority sends {item} from channel {i}')
                    yield item
                    print(f'Priority done')
                    break

        await clk()

    @gear
    async def f(din0: Uint['T'], din1: Uint['T'], *, skip) -> Uint['T']:
        async with din0 as item0:
            print(f'f got {item0} on din0')
            for i in range(skip + 1):
                async with din1 as item1:
                    print(f'f got {item1} on din1')
                    if i == skip:
                        yield item0 + item1
                        print(f'f sent {item0 + item1}')

    stim0 = seqr(t=Uint[16], seq=[10]*4) \
        | drv

    stim1 = seqr(t=Uint[16], seq=list(range(8))) \
        | drv

    (f(stim0, stim1, skip=1), stim1) \
        | priority_mux \
        | check(ref=[1, 4, 7, 10])

    sim()


test_general()
