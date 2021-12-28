from pygears import alternative, gear
from pygears.typing import Tuple, Uint, Any, Queue, bitw
from pygears.util.utils import qrange
# from pygears.lib.rng import qrange


@gear
async def serialize(din: Tuple[{
        'data': Any,
        'active': Uint
}]) -> Queue['din["data"][0]']:
    async with din as (data, active):
        for i, last in qrange(active):
            yield data[i], last


@alternative(serialize)
@gear
async def serialize_plain(din) -> Queue['din[0]']:
    i = Uint[bitw(len(din.dtype) - 1)](0)

    async with din as val:
        for i, last in qrange(len(din.dtype)):
            yield val[i], last
