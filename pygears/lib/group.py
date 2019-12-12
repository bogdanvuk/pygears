from pygears import gear, alternative
from pygears.typing import Queue, Uint


@gear(hdl={'compile': True})
async def group(din: Queue, size: Uint, *,
                init=1) -> Queue['din.data', 'din.lvl + 1']:

    cnt = size.dtype(init)

    async with size as c:
        assert c >= init, 'group: incorrect configuration'
        last = False
        while not last:
            async for (data, eot) in din:
                last = (cnt == c)
                out_eot = last @ eot
                yield (data, out_eot)
                if not last:
                    cnt += int(eot)


@alternative(group)
@gear(hdl={'compile': True})
async def group_other(din, size: Uint, *, init=1) -> Queue['din']:
    cnt = size.dtype(init)

    async with size as c:
        assert c >= init, 'group: incorrect configuration'
        last = False
        while not last:
            async with din as data:
                last = (cnt == c)
                yield (data, last)
                cnt += 1
