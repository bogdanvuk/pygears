from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'compile': True, 'inline_conditions': True})
async def qcnt(din: Queue, *, lvl=1, init=1, w_out=16) -> Queue[Uint['w_out']]:
    """Short for Queue Count. Counts the number of sub-transactions in the input
    transaction and outputs the running count.

    Args:
        lvl: Specifies the level of the input Queue that needs to be counted
        init: Initialization value for the counter
        w_out: Width of the counter and the output data bus

    Returns:
        The running count of sub-transactions in the input transaction.
    """
    cnt = Uint[w_out](init)

    async for (data, eot) in din:
        if all(eot[:din.dtype.lvl - lvl]):
            yield (cnt, all(eot))
            cnt += 1
