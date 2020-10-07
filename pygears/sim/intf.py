from pygears.core.graph import get_consumer_tree
from pygears import GearDone
from pygears.conf import PluginBase, reg
from pygears.core.sim_event import SimEvent
from pygears.typing import TypeMatchError
from pygears.typing import typeof, Any

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


class SimIntf:
    def __init__(self, intf):
        self.intf = intf
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
    def dtype(self):
        return self.intf.dtype

    @property
    def consumers(self):
        return self.intf.consumers

    @property
    def producer(self):
        return self.intf.producer

    @property
    def basename(self):
        return self.intf.basename

    @property
    def parent(self):
        return self.intf.parent

    @property
    def name(self):
        if not self.parent:
            return None

        return f'{self.parent.name}.{self.basename}'

    def __repr__(self):
        return f'SimIntf({repr(self.dtype)})'

    def __str__(self):
        return f'SimIntf({self.dtype})'

    @property
    def end_consumers(self):
        return self.intf.end_consumers

    @property
    def end_producer(self):
        return self.intf.end_producer

    @property
    def in_queue(self):
        return self.intf.in_queue

    @property
    def out_queues(self):
        return self.intf.out_queues

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
            if c.consumer._done:
                raise GearDone

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
        for q in self.out_queues:
            if q._unfinished_tasks:
                return False

        return True

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
        if not self.in_queue._unfinished_tasks:
            return

        e = self.events['ack']
        if e:
            e(self)

        self.in_queue.task_done()
        if self.in_queue.intf.ready_nb():
            e = self.in_queue.intf.events['ack']
            e(self.in_queue.intf)

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

    async def __aiter__(self):
        while True:
            data = await self.pull()

            yield data

            self.ack()

            if all(data.eot):
                break

    def __hash__(self):
        return id(self)


class IntfOperPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['gear/intf_oper'] = {}
        global gear_reg
        gear_reg = reg['gear']
