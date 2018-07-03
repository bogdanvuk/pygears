from pygears import gear
from pygears.typing import Queue, Tuple, Uint


@gear
async def replicate(din: Tuple[Uint['w_len'], 'w_val']) -> Queue['w_val']:
    async with din as val:
        for i in range(val[0]):
            yield (val[1], i == (val[0] - 1))
