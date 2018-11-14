from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def qcnt(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
    cnt = 0
    async for (data, eot) in din:
        if all(eot[:din.dtype.lvl - lvl]):
            yield (cnt, all(eot))
            cnt += 1
