from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def chop(din: Queue['data_t'], cfg: Uint['w_cfg']) -> Queue['data_t', 2]:

    i = 0
    val = (0, 0)

    async with cfg as size:
        while (val[1] == 0):
            i += 1
            async with din as val:
                yield (val[0], val[1] or (i % size == 0), val[1])
