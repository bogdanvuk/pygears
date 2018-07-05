import inspect

from pygears import gear
from pygears.sim import clk
from pygears.typing import TLM
from pygears.util.utils import quiter
from pygears.sim.utils import SimDelay


class TypingYieldVisitorBase:
    def visit(self, data, dtype):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)
        ret = visit_func(data, dtype)
        if inspect.isgenerator(ret):
            yield from ret
        else:
            yield ret

    def visit_default(self, data, dtype):
        yield data


class TypeDrvVisitor(TypingYieldVisitorBase):
    def visit_queue(self, data, dtype):
        for (i, d), eot in quiter(enumerate(data)):
            for ret in self.visit(d, dtype[:-1]):
                if dtype.lvl == 1:
                    yield (ret, eot)
                else:
                    yield (ret[0], *ret[1:], eot)


@gear
async def drv(din: TLM['t'], *, t=b't', delay=SimDelay(0, 0)) -> b't':
    while 1:
        async with din as item:
            for d in TypeDrvVisitor().visit(item, t):
                for i in range(delay.delay):
                    await clk()
                yield t(d)

    print("Driver done")
