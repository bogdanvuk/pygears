from pygears import alternative, gear
from pygears.typing import Tuple, Uint, Any, Queue
# from pygears.util.utils import qrange
from pygears.lib.rng import qrange


@gear(hdl={'compile': True})
async def serialize(din: Tuple[{
        'data': Any,
        'active': Uint
}]) -> Queue['din["data"][0]']:
    async with din as (data, active):
        async for i, last in qrange(active):
            yield data[i], last


@alternative(serialize)
@gear(hdl={'compile': True})
async def serialize_plain(din) -> Queue['din[0]']:
    async with din as val:
        async for i, last in qrange(len(din.dtype)):
            yield val[i], last
