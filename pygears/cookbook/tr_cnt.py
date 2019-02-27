from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'compile': True})
async def tr_cnt(din: Queue['t_data'], cfg: Uint['t_cfg'], *,
                 init=1) -> Queue['t_data', 2]:
    '''Transaction counter: counts the input eots. Number of eots to count
    given with cfg. When sufficent transactions are seen, returns ready on cfg
    and sets higher eot on output

    din -- Queue
    cfg -- how many transactions to count
    dout -- Queue, lvl 2: lower list same as input, higher list shows that
    transactions were counted
    '''

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
