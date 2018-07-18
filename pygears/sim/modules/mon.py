from pygears import gear
from pygears.sim import clk
from pygears.sim.utils import SimDelay
from pygears.typing import TLM


class Partial:
    def __new__(cls, val):
        if isinstance(val, Partial):
            return val
        else:
            obj = super().__new__(cls)
            obj.__init__(val)
            return obj

    def __init__(self, val):
        self._val = val

    @property
    def val(self):
        return self._val


class TypeMonitorVisitor:
    def __init__(self, dtype):
        self.data = None
        self.dtype = dtype

    def __bool__(self):
        return isinstance(self.data, Partial)

    def append(self, elem):
        self.data = self.visit(self.data, elem, self.dtype)
        return self.data

    def visit(self, data, elem, dtype):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)

        return visit_func(data, elem, dtype)

    def visit_default(self, data, elem, dtype):
        return elem

    def visit_queue(self, data, elem, dtype):
        if dtype.lvl == 1:
            sub_elem = elem[0]
        else:
            sub_elem = elem[:-1]

        if not data:
            sub_data = None
            data = []
        else:
            data = data.val
            if isinstance(data[-1], Partial):
                sub_data = data.pop()
            else:
                sub_data = None

        sub_data = self.visit(sub_data, sub_elem, dtype[:-1])
        data.append(sub_data)

        eot = elem[-1]
        if eot and (not isinstance(sub_data, Partial)):
            return data
        else:
            return Partial(data)


@gear
async def mon(din, *, t=b'din') -> TLM['din']:
    v = TypeMonitorVisitor(t)
    while 1:
        data = None
        while (isinstance(data, Partial) or data is None):
            # print('Monitor waiting')
            item = await din.get()
            # print('Monitor got: ', item)
            data = v.visit(data, item, t)

        # print('Monitor emits: ', data)
        yield data


@gear
async def delay_mon(din, *, t=b'din', delay=SimDelay(0, 0)) -> b'din':
    async with din as item:
        await delay.delay
        yield item
