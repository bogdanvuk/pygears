import inspect

from pygears import GearDone, gear
from pygears.util.utils import quiter

# from pygears.sim.extens.svrand import get_rand_data


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
async def drv(*, t, seq) -> b't':
    """Outputs one data at the time from the iterable ``seq`` cast to the type
    ``t``.

    Args:
        t: Type of the data to output
        seq: An iterable generating data to be output

    Returns:
        Data of the type ``t``

    >>> drv(t=Uint[8], seq=range(10))

    If ``t`` is a :class:`Queue` type of certain level, then ``seq`` should
    generate nested iterables of the same level::

        q1 = ((11, 12), (21, 22, 23))
        q2 = ((11, 12, 13))

    >>> drv(t=Queue[Uint[8], 2], seq=[q1, q2])
    """

    for val in seq:
        if type(val) == t:
            yield val
        else:
            for d in TypeDrvVisitor().visit(val, t):
                yield t(d)

    raise GearDone


@gear
async def secdrv(seqin, *, t) -> b't':
    async with seqin as seq:
        for val in seq:
            if type(val) == t:
                yield val
            else:
                for d in TypeDrvVisitor().visit(val, t):
                    yield t(d)


# @gear
# async def drv_rand_queue(*, tout, data_func,
#                          eot_con_name='din_eot') -> b'tout':
#     eot = 0
#     while eot != int('1' * tout.lvl, 2):
#         eot = get_rand_data(eot_con_name)
#         yield tout((data_func(), *eot))

#     raise GearDone
