import asyncio

from .graph import get_consumer_tree, get_producer_queue, get_end_producer
from pygears import GearDone
from pygears.conf import PluginBase, reg, MultiAlternativeError
from pygears.core.port import InPort, OutPort, HDLConsumer, HDLProducer
from pygears.core.partial import Partial
from pygears.core.sim_event import SimEvent
from pygears.typing import TypeMatchError
from pygears.typing import typeof, Any
from pygears.typing.base import TypingMeta
from pygears.conf import inject, Inject
from .graph import get_sim_map_gear

gear_reg = {}


def operator_func_from_namespace(cls, name):
    def wrapper(self, *args, **kwargs):
        if name not in reg['gear/intf_oper']:
            raise Exception(f'Operator {name} is not supported.')

        operator_func = reg[f'gear/intf_oper/{name}']
        return operator_func(self, *args, **kwargs)

    return wrapper


def operator_methods_gen(cls):
    for name in cls.OPERATOR_SUPPORT:
        setattr(cls, name, operator_func_from_namespace(cls, name))
    return cls


@operator_methods_gen
class Intf:
    OPERATOR_SUPPORT = [
        '__getitem__', '__neg__', '__add__', '__and__', '__div__', '__eq__', '__floordiv__',
        '__ge__', '__gt__', '__invert__', '__le__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__lshift__', '__rshift__', '__aiter__', '__sub__', '__xor__', '__truediv__',
        '__matmul__'
    ]

    def __init__(self, dtype):
        self.consumers = []
        self._end_consumers = None
        self._end_producer = None
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

    @property
    def sole_intf(self):
        if self.producer:
            return len(self.producer.gear.out_ports) == 1
        else:
            return True

    @property
    def is_broadcast(self):
        return len(self.consumers) > 1

    @property
    def basename(self):
        producer_port = self.producer
        if isinstance(producer_port, HDLProducer):
            #TODO: Not really a producer port
            producer_port = self.consumers[0]

        port_name = producer_port.basename

        if isinstance(producer_port, InPort):
            return port_name
        elif ((not self.is_broadcast) and self.consumers
              and isinstance(self.consumers[0], OutPort)):
            return self.consumers[0].basename
        elif hasattr(self, 'var_name'):
            return self.var_name
        elif self.sole_intf:
            return f'{producer_port.gear.basename}'
        else:
            return f'{producer_port.gear.basename}_{port_name}'

    @property
    def parent(self):
        if isinstance(self.producer, InPort):
            return self.producer.gear
        elif isinstance(self.producer, OutPort):
            return self.producer.gear.parent
        elif len(self.consumers) == 1 and isinstance(self.consumers[0], OutPort):
            return self.consumers[0].gear

    @property
    def name(self):
        if not self.parent:
            return None

        return f'{self.parent.name}.{self.basename}'

    def __ior__(self, iout):
        if isinstance(iout, Partial):
            raise Exception(f"Output of the unresolved gear '{iout.func.__name__}' with"
                            f" arguments {iout.args} and parameters {iout.kwds},"
                            f" connected to '{self}': {str(MultiAlternativeError(iout.errors))}")
        elif not isinstance(iout, Intf):
            raise Exception(f"Cannot connect to {iout}")

        if iout.dtype != self.dtype:
            raise TypeError(f'Output interface of type "{repr(iout.dtype)}", cannot be connected '
                            f'to the interface of type "{repr(self.dtype)}"')

        iout.producer.consumer = self
        if self.producer is not None:
            raise Exception(
                f"Interface '{self}' is already connected to a producer '{self.producer.name}'\n")

        self.producer = iout.producer

        return self

    def __or__(self, other):
        if isinstance(other, Intf):
            raise Exception(f'Cannot connect interface {self} to the interface {other}\n'
                            f'Did you mean to connect to "{other.producer.gear.name}"?')

        if not (isinstance(other, (str, TypingMeta)) or (other is int) or (other is float)):
            return other.__ror__(self)

        operator_func = reg['gear/intf_oper/__or__']
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
        if self.consumers and isinstance(self.consumers[0], HDLConsumer):
            self.consumers.clear()

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
    def end_producer(self):
        if self._end_producer is None:
            self._end_producer = get_end_producer(self)

        return self._end_producer

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
            asyncio.Queue(maxsize=1, loop=reg['sim/simulator']) for _ in self.end_consumers
        ]

        for i, q in enumerate(self._out_queues):
            q.intf = self
            q.index = i

        return self._out_queues

    def put_nb(self, val):
        put_event = self.events['put']

        if self.dtype is not type(val):
            err = None
            try:
                if not typeof(self.dtype, Any):
                    val = self.dtype(val)
            except (TypeError, ValueError) as e:
                err = e

            if err:
                # TODO: when value cannot be represented, the error report can be terse
                raise TypeMatchError(f'{str(err)}\n, when converting output data "{repr(val)}"'
                                     f' from the "{reg["gear/current_module"].name}"'
                                     f' module to the type {repr(self.dtype)}')

        if put_event:
            put_event(self, val)

        for q, c in zip(self.out_queues, self.end_consumers):
            if c.consumer is None or c.consumer._done:
                raise GearDone

            put_event = c.consumer.events['put']
            if put_event:
                put_event(c.consumer, val)

            q.put_nowait(val)

    async def ready(self):
        gear_reg['current_sim'].phase = 'back'
        for q in self._out_queues:
            if q._unfinished_tasks:
                await q.join()

    def ready_nb(self):
        for q in self.out_queues:
            if q._unfinished_tasks:
                return False

        return True

    async def send(self, val):
        if reg['sim/simulator'].phase != 'forward':
            from pygears.sim import clk
            await clk()

        self.put_nb(val)

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
        ev = self.events
        e = ev['pull_start']
        if e:
            e(self)

        if self._done:
            raise GearDone

        val = self._data
        if val is None:
            gear_reg['current_sim'].phase = 'forward'
            val = await self.in_queue.get()

        e = ev['pull_done']
        if e:
            e(self)

        self._data = val
        if isinstance(val, self.dtype):
            return val

        try:
            return self.dtype(val)
        except TypeError:
            return val

    def ack(self):
        inq = self.in_queue
        if not inq._unfinished_tasks:
            return

        e = self.events['ack']
        if e:
            e(self)

        inq.task_done()
        if inq.intf.ready_nb():
            e = inq.intf.events['ack']
            e(inq.intf)

        self._data = None
        return

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
        reg['gear/intf_oper'] = {}
        global gear_reg
        gear_reg = reg['gear']._dict
