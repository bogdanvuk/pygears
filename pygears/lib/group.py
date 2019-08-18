from pygears import gear, alternative
from pygears.typing import Queue, Uint


@gear(hdl={'compile': True})
async def group(din: Queue, size: Uint, *,
                init=1) -> Queue['din.data', 'din.lvl + 1']:
    """Short for transaction counter, counts the input transactions. The number
    of transactions counted on the ``din`` input is given with the ``size``
    input. When sufficent transactions are seen, ready is returned on ``size``
    and ``din`` blocks until the next configuration is available.

    Args: init: Initialization value for the counter

    Returns: A level 2 Queue type whose data consists of the input data, but
        the highest `eot` signalizes that sufficent transactions have been
        counted. """

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
