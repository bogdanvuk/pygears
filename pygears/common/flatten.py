from pygears import gear, alternative
from pygears.typing import Queue
from pygears.typing_common.flatten import flatten as type_flatten
from pygears.sim import cur_gear

from functools import reduce


@gear
async def flatten(din: Queue['tdin', 'din_lvl'],
                  *,
                  lvl=1,
                  dout_lvl=b'din_lvl - lvl') -> b'Queue[tdin, dout_lvl]':

    outtype = cur_gear().out_ports[0].dtype

    async with din as d:
        dout = [d[0]]
        if lvl > 1:
            dout.append(reduce(lambda x, y: x & y, d[1:lvl]))

        if lvl < din.dtype.lvl:
            dout += list(d[lvl + 1:])

        if len(dout) == 1:
            dout = dout[0]

        yield outtype(dout)


@alternative(flatten)
@gear(enablement=b'issubclass(din, Tuple)')
def flatten_tuple(din, *, lvl=1):
    return din | type_flatten(din.dtype, lvl)
