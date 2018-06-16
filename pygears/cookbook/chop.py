from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def chop(din: Queue['data_t'], cfg: Uint['w_cfg']) -> Queue['data_t', 2]:

    async with cfg as size:
        for i in range(size):
            async with din as val:
                print(f"Chop received {val}")
                yield val
