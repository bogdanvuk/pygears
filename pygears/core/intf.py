import asyncio

from pygears import registry, GearDone
from pygears.core.port import InPort, OutPort
from pygears.registry import PluginBase
from pygears.core.sim_event import SimEvent


def operator_func_from_namespace(cls, name):
    def wrapper(self, *args, **kwargs):
        try:
            operator_func = registry('IntfOperNamespace')[name]
            return operator_func(self, *args, **kwargs)
        except KeyError as e:
            raise Exception(f'Operator {name} is not supported.')

    return wrapper


def operator_methods_gen(cls):
    for name in cls.OPERATOR_SUPPORT:
        setattr(cls, name, operator_func_from_namespace(cls, name))
    return cls


def _get_consumer_tree_rec(intf, consumers):
    for port in intf.consumers:
        cons_intf = port.consumer
        if (port.gear in registry('SimMap')) and (isinstance(port, InPort)):
            # if not cons_intf.consumers:
            consumers.append(port)
        else:
            _get_consumer_tree_rec(cons_intf, consumers)


def get_consumer_tree(intf):
    consumers = []
    _get_consumer_tree_rec(intf, consumers)
    return consumers


@operator_methods_gen
class Intf:
    OPERATOR_SUPPORT = [
        '__or__', '__getitem__', '__neg__', '__add__', '__sub__', '__mul__',
        '__div__', '__floordiv__', '__mod__', '__invert__', '__rshift__'
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
            'cancel': SimEvent()
        }

    def __ior__(self, iout):
        return iout.__matmul__(self)

    def __matmul__(self, iout):
        self.producer.consumer = iout
        iout.producer = self.producer

        return iout

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

    @property
    def end_consumers(self):
        if self._end_consumers is None:
            self._end_consumers = get_consumer_tree(self)

        return self._end_consumers

    @property
    def in_queue(self):
        if self._in_queue is None:
            if self.producer is not None:
                self._in_queue = self.producer.get_queue()

        return self._in_queue

    def get_consumer_queue(self, port):
        for pout in self.consumers:
            if pout.gear in registry('SimMap') and (isinstance(pout, OutPort)):
                out_queues = self.out_queues
                try:
                    i = self.end_consumers.index(port)
                except Exception as e:
                    print(
                        f'Port {port.gear.name}.{port.basename} not in end consumer list of {self.consumers[0].gear.name}.{self.consumers[0].basename}'
                    )
                    raise e
                return out_queues[i]
        else:
            if self.producer:
                return self.producer.get_queue(port)
            else:
                raise Exception(
                    f'Interface path does not end with a simulation gear at {pout.gear.name}.{pout.basename}'
                )

    @property
    def out_queues(self):
        if self._out_queues:
            return self._out_queues

        # if len(self.consumers) == 1 and self.in_queue:
        # if self.producer is not None:
        #     return [self.in_queue]
        # else:
        self._out_queues = [
            asyncio.Queue(maxsize=1) for _ in self.end_consumers
        ]

        for i, q in enumerate(self._out_queues):
            q.intf = self
            q.index = i

        return self._out_queues

    def put_nb(self, val):
        if any(registry('SimMap')[c.gear].done for c in self.end_consumers):
            raise GearDone

        self.events['put'](self, val)
        for q, c in zip(self.out_queues, self.end_consumers):
            self.events['put'](c.consumer, val)
            q.put_nowait(val)

    async def ready(self):
        if not self.ready_nb():
            for q, c in zip(self.out_queues, self.end_consumers):
                registry('CurrentModule').phase = 'back'
                await q.join()
                # self.events['ack'](c.consumer)

            # self.events['ack'](self)
        # print(f"All acks received")

    def ready_nb(self):
        return all(not q._unfinished_tasks for q in self.out_queues)
        # if ready:
        #     self.events['ack'](self)

        # return ready

    async def put(self, val):
        self.put_nb(val)
        await self.ready()

    def empty(self):
        if self._data is not None:
            return False
        else:
            return self.in_queue.empty()
        # intf, index = self.in_queue
        # return intf.out_queues[index].empty()

    def finish(self):
        self._done = True
        for q, c in zip(self.out_queues, self.end_consumers):
            c.finish()
            for task in q._getters:
                self.events['cancel'](self, c)
                task.cancel()

    def done(self):
        return self._done

    def pull_nb(self):
        if self._done:
            raise GearDone

        if self._data is None:
            self._data = self.in_queue.get_nowait()

        return self._data

    def get_nb(self):
        val = self.pull_nb()
        self.ack()
        return val

    async def pull(self):
        self.events['pull_start'](self)
        if self._done:
            raise GearDone

        if self._data is None:
            self._data = await self.in_queue.get()

        self.events['pull_done'](self)
        return self._data

    def ack(self):
        self.events['ack'](self)
        ret = self.in_queue.task_done()
        if self.in_queue.intf.ready_nb():
            self.events['ack'](self.in_queue.intf)

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
        cls.registry['IntfOperNamespace'] = {}
