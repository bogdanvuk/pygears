from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'compile': True})
async def qcnt(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
    cnt = Uint[w_out](0)
    async for (data, eot) in din:
        if all(eot[:din.dtype.lvl - lvl]):
            cnt += 1
            yield (cnt, all(eot))
