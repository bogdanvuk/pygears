from pygears import alternative, gear
from pygears.typing import Array, Tuple, Uint, bitw
from pygears.util.utils import qrange


@gear(svgen={'compile': True})
async def serialize(din: Array) -> b'din.dtype':
    i = Uint[bitw(len(din.dtype))](0)

    async with din as val:
        for i in range(len(val)):
            yield val[i]


TDin = Tuple[{'data': Array['t_data', 'no'], 'active': Uint['w_active']}]


@alternative(serialize)
@gear(svgen={'compile': True})
async def active_serialize(din: TDin) -> b'Queue[t_data]':
    i = Uint[din.dtype[1]](0)

    async with din as (data, active):
        for i, last in qrange(active):
            yield data[i], last
