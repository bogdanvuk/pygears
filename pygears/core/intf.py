import asyncio

from .graph import get_consumer_tree, get_producer_queue
from pygears import GearDone
from pygears.conf import PluginBase, registry, safe_bind
from pygears.core.port import InPort, OutPort
from pygears.core.sim_event import SimEvent
from .type_match import TypeMatchError
from pygears.typing import typeof, Any
from pygears.typing.base import TypingMeta
from pygears.conf import inject, Inject
from .graph import get_sim_map_gear

gear_reg = {}


def operator_func_from_namespace(cls, name):
    def wrapper(self, *args, **kwargs):
        if name not in registry('gear/intf_oper'):
            raise Exception(f'Operator {name} is not supported.')

        operator_func = registry(f'gear/intf_oper/{name}')
        return operator_func(self, *args, **kwargs)

    return wrapper


def operator_methods_gen(cls):
    for name in cls.OPERATOR_SUPPORT:
        setattr(cls, name, operator_func_from_namespace(cls, name))
    return cls


@operator_methods_gen
class Intf:
    OPERATOR_SUPPORT = [
        '__getitem__', '__neg__', '__add__', '__and__', '__div__', '__eq__',
        '__floordiv__', '__ge__', '__gt__', '__invert__', '__le__', '__lt__',
        '__mod__', '__mul__', '__ne__', '__neg__', '__lshift__', '__rshift__',
        '__aiter__', '__sub__', '__xor__', '__truediv__', '__matmul__'
    ]

    def __init__(self, dtype):
        self.consumers = []
        self._end_consumers = None
        self.dtype = dtype
        self.producer = None
        self._in_queue = None
        self._out_queues = []
        self._done = False
        self._data = None

        self.events = {
            'put': SimEvent(),
            'put_out': SimEvent(),
            'ack': SimEvent(),
            'ack_in': SimEvent(),
            'pull_start': SimEvent(),
            'pull_done': SimEvent(),
            'finish': SimEvent()
        }

    def __ior__(self, iout):
        iout.producer.consumer = self
        if self.producer is not None:
            raise Exception(
                f"Interface '{self}' is already connected to a producer '{self.producer.name}'\n")

        self.producer = iout.producer

        return self

    def __or__(self, other):
        if isinstance(other, Intf):
            raise Exception(
                f'Cannot connect interface {self} to the interface {other}\n'
                f'Did you mean to connect to "{other.producer.gear.name}"?')

        if not (isinstance(other, (str, TypingMeta)) or (other is int) or
                (other is float)):
            return other.__ror__(self)

        operator_func = registry('gear/intf_oper/__or__')
        return operator_func(self, other)

    def source(self, port):
        self.producer = port
        port.consumer = self

    def disconnect(self, port):
        if port in self.consumers:
            self.consumers.remove(port)
            port.producer = None
        elif port == self.producer:
            port.consumer = None
            self.producer = None

    def connect(self, port):
        self.consumers.append(port)
        port.producer = self

    def __repr__(self):
        return f'Intf({repr(self.dtype)})'

    def __str__(self):
        return f'Intf({self.dtype})'

    @property
    def end_consumers(self):
        if self._end_consumers is None:
            self._end_consumers = get_consumer_tree(self)

        return self._end_consumers

    @property
    def in_queue(self):
        if self._in_queue is None:
            if self.producer is not None:
                # self._in_queue = self.producer.get_queue()
                self._in_queue = get_producer_queue(self)

        return self._in_queue

    @property
    def out_queues(self):
        if self._out_queues:
            return self._out_queues

        self._out_queues = [
            asyncio.Queue(maxsize=1, loop=registry('sim/simulator'))
            for _ in self.end_consumers
        ]

        for i, q in enumerate(self._out_queues):
            q.intf = self
            q.index = i

        return self._out_queues

    def put_nb(self, val):
        if any(get_sim_map_gear(c.gear).done for c in self.end_consumers):
            raise GearDone

        put_event = self.events['put']

        if self.dtype is not type(val):
            try:
                if not typeof(self.dtype, Any):
                    val = self.dtype(val)
            except TypeError:
                raise TypeMatchError(
                    f'Output data "{repr(val)}" from the'
                    f' "{registry("gear/current_module").name}"'
                    f' module cannot be converted to the type'
                    f' {repr(self.dtype)}')

        if put_event:
            put_event(self, val)

        for q, c in zip(self.out_queues, self.end_consumers):
            put_event = c.consumer.events['put']
            if put_event:
                put_event(c.consumer, val)

            q.put_nowait(val)

    async def ready(self):
        if not self.ready_nb():
            for q, c in zip(self.out_queues, self.end_consumers):
                gear_reg['current_sim'].phase = 'back'
                await q.join()

    def ready_nb(self):
        return all(not q._unfinished_tasks for q in self.out_queues)

    async def put(self, val):
        self.put_nb(val)
        await self.ready()

    def empty(self):
        if self._data is not None:
            return False
        else:
            return self.in_queue.empty()

    def finish(self):
        '''Mark the interface as done, i.e. no more data will be transmitted.

        Informs also all consumer ports. If any task is waiting for this
        interface's data it is finishled. This is how the end of simulation
        propagates from the producers to the consumers.
        '''

        self.events['finish'](self)
        self._done = True
        for q, c in zip(self.out_queues, self.end_consumers):
            c.finish()
            for task in q._getters:
                task.cancel()

    @property
    def done(self):
        return self._done

    def pull_nb(self):
        if self._done:
            raise GearDone

        if self._data is None:
            self._data = self.in_queue.get_nowait()

        if isinstance(self._data, self.dtype):
            return self._data

        try:
            return self.dtype(self._data)
        except TypeError:
            return self._data

    def get_nb(self):
        val = self.pull_nb()
        self.ack()
        return val

    async def pull(self):
        e = self.events['pull_start']
        if e:
            e(self)

        if self._done:
            raise GearDone

        if self._data is None:
            gear_reg['current_sim'].phase = 'forward'
            self._data = await self.in_queue.get()

        e = self.events['pull_done']
        if e:
            e(self)

        if isinstance(self._data, self.dtype):
            return self._data

        try:
            return self.dtype(self._data)
        except TypeError:
            return self._data

    def ack(self):
        e = self.events['ack']
        if e:
            e(self)

        ret = self.in_queue.task_done()
        if self.in_queue.intf.ready_nb():
            e = self.in_queue.intf.events['ack']
            e(self.in_queue.intf)

        self._data = None
        return ret

    async def get(self):
        val = await self.pull()
        self.ack()
        return val

    async def __aenter__(self):
        return await self.pull()

    async def __aexit__(self, exception_type, exception_value, traceback):
        if exception_type is None:
            self.ack()

    def __hash__(self):
        return id(self)


class IntfOperPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper', {})
        global gear_reg
        gear_reg = registry('gear')
