from pygears import gear, alternative, module
from pygears.typing import Queue
from pygears.typing_common.flatten import flatten as type_flatten
from operator import and_

from functools import reduce


def flatten_func(d, lvl):
    dout_lvl = d.lvl - lvl

    dout = [d[0]]
    if lvl > 1:
        dout.append(reduce(and_, d[1:lvl + 2]))

    if dout_lvl > 1:
        dout += list(d[lvl + 2:])

    if len(dout) == 1:
        dout = dout[0]

    return Queue[type(d)[0], dout_lvl](dout)


@gear
async def flatten(din: Queue['tdin', 'din_lvl'],
                  *,
                  lvl=1,
                  dout_lvl=b'din_lvl - lvl') -> b'Queue[tdin, dout_lvl]':

    async with din as d:
        yield flatten_func(d, lvl)


@alternative(flatten)
@gear(enablement=b'issubclass(din, Tuple)')
def flatten_tuple(din, *, lvl=1):
    return din | type_flatten(din.dtype, lvl)
