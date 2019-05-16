from pygears import alternative, gear
from pygears.typing import Array, Tuple, Uint
from pygears.util.utils import qrange


@gear(hdl={'compile': True})
async def serialize(din: Array) -> b'din.dtype':
    async with din as val:
        for i in range(len(din.dtype)):
            yield val[i]


TDin = Tuple[{'data': Array['t_data', 'no'], 'active': Uint['w_active']}]


@alternative(serialize)
@gear(hdl={'compile': True})
async def active_serialize(din: TDin) -> b'Queue[t_data]':
    i = Uint[din.dtype['active']](0)

    async with din as (data, active):
        for i, last in qrange(active):
            yield data[i], last
