from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def chop(din: Queue['data_t'], cfg: Uint['w_cfg']) -> Queue['data_t', 2]:

    i = 0
    val = din.dtype((0, 0))

    async with cfg as size:
        while (val.eot == 0):
            i += 1
            async with din as val:
                yield (val.data, val.eot or (i % size == 0), val.eot)
