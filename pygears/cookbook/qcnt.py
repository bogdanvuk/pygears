from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def qcnt(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
    val = (0, ) * din.dtype.lvl
    cnt = 0
    last_el = False
    while not last_el:
        async with din as val:
            last_el = all(v for v in val[1:])
            cnt_mode = True if (lvl == din.dtype.lvl) else all(
                v for v in val[1:din.dtype.lvl - lvl + 1])
            if cnt_mode:
                yield (cnt, last_el)
                cnt += 1
