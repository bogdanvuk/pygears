from pygears import gear, module
from pygears.typing import Queue


@gear
async def tr_cnt(din: Queue['TData'], cfg: 'TCfg') -> Queue['TData', 2]:
    '''Transaction counter: counts the input eots. Number of eots to count
    given with cfg. When sufficent transactions are seen, returns ready on cfg
    and sets higher eot on output

    din -- Queue
    cfg -- how many transactions to count
    dout -- Queue, lvl 2: lower list same as input, higher list shows that
    transactions were counted
    '''

    cnt = 0
    val = din.dtype((0, 0))

    async with cfg as c:
        while not (val.eot and (cnt == c)):
            async with din as val:
                yield module().tout((val.data, val.eot, (cnt == (c - 1))))
                cnt += val.eot
