from pygears import gear, alternative, module
from pygears.typing import Queue, Bool
from pygears.typing.flatten import flatten as type_flatten
from operator import and_

from functools import reduce


def flatten_func(d, lvl):
    dout_lvl = d.lvl - lvl

    if dout_lvl == 0:
        return d.data
    else:
        eot = d.eot[lvl+1:] @ Bool(reduce(and_, d.eot[:lvl+1]))
        return Queue[type(d.data), dout_lvl](d.data, eot)


@gear
async def flatten(din: Queue,
                  *,
                  lvl=1,
                  dout_lvl=b'din.lvl - lvl') -> b'Queue[din.data, dout_lvl]':
    async with din as d:
        yield flatten_func(d, lvl)


@alternative(flatten)
@gear(enablement=b'issubclass(din, Tuple)')
def flatten_tuple(din, *, lvl=1):
    return din >> type_flatten(din.dtype, lvl)
