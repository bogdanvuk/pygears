import inspect

from pygears import gear, GearDone
from pygears.typing import TLM
from pygears.util.utils import quiter
from pygears.sim.utils import SimDelay
from pygears.sim.extens.svrand import get_rand_data


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
                await delay.delay
                yield t(d)

    print("Driver done")


@gear
async def drv_rand_queue(*, tout, data_func,
                         eot_con_name='din_eot') -> b'tout':
    eot = 0
    while eot != int('1' * tout.lvl, 2):
        eot = get_rand_data(eot_con_name)
        yield tout((data_func(), *eot))

    raise GearDone
