from pygears import gear
from pygears.util.utils import qrange
from pygears.typing import Queue, Tuple, Uint


@gear(svgen={'compile': True})
async def replicate(din: Tuple[Uint['w_len'], 'w_val']) -> Queue['w_val']:
    i = din.dtype[0](0)

    async with din as (length, value):
        for i, last in qrange(length):
            yield (value, last)
