from pygears import gear, alternative
from pygears.typing import Queue, Uint


@gear(enablement=b'running==False')
async def qcnt(din: Queue, *, running=False, lvl=0, init=1,
               w_out=16) -> Uint['w_out']:
    """Short for Queue Length Count. Counts the number of input sub-transactions
    and outputs the final count when the input transaction finishes.

    Args:
        lvl: Specifies the level of the input Queue that needs to be counted
        init: Initialization value for the counter
        w_out: Width of the counter and the output data bus

    Returns:
        The number of sub-transactions in the input transaction.
    """

    cnt = Uint[w_out](init)

    async for (data, eot) in din:
        if all(eot):
            yield cnt

        if all(eot[:lvl]):
            cnt += 1


@alternative(qcnt)
@gear(enablement=b'running==True')
async def qcnt_running(din: Queue, *, running=True, lvl=0, init=1,
                       w_out=16) -> Queue[Uint['w_out']]:
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
        if all(eot[:lvl]):
            yield (cnt, all(eot))
            cnt += 1
