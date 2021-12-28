from pygears import gear, alternative
from pygears.typing import Queue, Uint, Bool


@gear
async def group(din: Queue, size: Uint, *,
                init=1) -> Queue['din.data', 'din.lvl + 1']:

    cnt = size.dtype(init)
    last: Bool
    out_eot: Uint[din.dtype.lvl+1]

    async with size as c:
        assert c >= init, 'group: incorrect configuration'
        last = False
        while not last:
            async for (data, eot) in din:
                last = (cnt == c)
                out_eot = last @ eot
                yield (data, out_eot)
                if not last and all(eot):
                    cnt += 1


@alternative(group)
@gear
async def group_other(din, size: Uint, *, init=1) -> Queue['din']:
    cnt = size.dtype(init)
    last: Bool

    async with size as c:
        assert c >= init, 'group: incorrect configuration'
        last = False
        while not last:
            async with din as data:
                last = (cnt == c)
                yield (data, last)
                cnt += 1
