import inspect

from pygears import gear
from pygears.sim.sim import clk
from pygears.typing import TLM


def quiter(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, False
        last = val
    # Report the last value.
    yield last, True


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
async def drv(din: TLM['t'], *, t=b't') -> b't':
    while 1:
        async with din as item:
            for d in TypeDrvVisitor().visit(item, t):
                # print('Driver sends: ', d)
                yield d
                # print('Driver sent: ', d)
                await clk()
                # print('Driver waited for clock')

    print("Driver done")
