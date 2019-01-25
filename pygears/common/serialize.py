from pygears import alternative, gear, module
from pygears.typing import Array, Queue, Tuple, Uint, bitw
from pygears.util.utils import quiter


@gear(svgen={'compile': True})
async def serialize(din: Array) -> b'din.dtype':
    i = Uint[bitw(len(din.dtype))](0)

    async with din as val:
        for i in range(len(val)):
            yield val[i]


TDin = Tuple[Array[Uint['w_data'], 'no'], Uint['w_active']]
TOut = Queue[Uint['w_data']]


@alternative(serialize)
@gear
async def active_serialize(din: TDin,
                           *,
                           w_data=b'w_data',
                           no=b'no',
                           w_active=b'w_active') -> TOut:
    async with din as val:
        data, active = val
        active_out = [data[i] for i in range(len(data)) if i < active]
        for d, last in quiter(active_out):
            yield module().tout((d, last))
