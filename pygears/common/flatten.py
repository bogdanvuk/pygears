from pygears import gear, alternative
from pygears.typing import Queue
from pygears.typing_common.flatten import flatten as type_flatten

from functools import reduce


@gear
async def flatten(din: Queue['tdin', 'din_lvl'],
                  *,
                  lvl=1,
                  dout_lvl=b'din_lvl - lvl') -> b'Queue[tdin, dout_lvl]':
    async with din as d:
        dout = (d[0], ) \
               + (reduce(d[1:lvl], lambda x, y: x & y)) \
               + tuple(d[lvl + 1:])

        print("Flatten: ", dout)
        yield dout


@alternative(flatten)
@gear(enablement=b'issubclass(din, Tuple)')
def flatten_tuple(din, *, lvl=1):
    return din | type_flatten(din.dtype, lvl)
