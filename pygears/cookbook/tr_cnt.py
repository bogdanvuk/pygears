from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'compile': True, 'inline_conditions': True})
async def tr_cnt(din: Queue['t_data'], cfg: Uint['t_cfg'], *,
                 init=1) -> Queue['t_data', 2]:
    """Short for transaction counter, counts the input transactions. The number
    of transactions counted on the ``din`` input is given with the ``cfg`` input.
    When sufficent transactions are seen, ready is returned on ``cfg`` and ``din``
    blocks until the next configuration is available.

    Args:
        init: Initialization value for the counter

    Returns:
        A level 2 Queue type whose data consists of the input data, but the highest
          `eot` signalizes that sufficent transactions have been counted.
    """
    cnt = cfg.dtype(init)

    async with cfg as c:
        assert c >= init, 'tr_cnt: incorrect configuration'
        last = (cnt == c)
        while not last:
            async for (data, eot) in din:
                last = (cnt == c)
                out_eot = last @ eot
                yield (data, out_eot)
                if not last:
                    cnt += int(eot)
