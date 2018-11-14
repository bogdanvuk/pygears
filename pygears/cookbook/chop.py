from pygears import gear
from pygears.typing import Queue, Uint
from pygears.conf import gear_log


@gear
async def chop(din: Queue['data_t'], cfg: Uint['w_cfg']) -> Queue['data_t', 2]:

    i = 0
    val = din.dtype((0, 0))

    async with cfg as size:
        while (val.eot == 0):
            i += 1
            async with din as val:
                dout_sub = din.dtype(val.data, val.eot or (i % size == 0))
                dout = dout_sub.wrap(val.eot)

                gear_log().debug(f'Chop yielding {dout}')
                yield dout
