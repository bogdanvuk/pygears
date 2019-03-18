from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'compile': True})
async def qlen_cnt(din: Queue['tdin', 'din_lvl'],
                   *,
                   cnt_lvl=1,
                   cnt_one_more=False,
                   w_out=16) -> Uint['w_out']:
    """Short for Queue Length Count. Counts the number of input sub-transactions
    and outputs the final count when the input transaction finishes.

    Args:
        cnt_lvl: Specifies the level of the input Queue that needs to be counted
        cnt_one_more: If set count one value more than specified
        w_out: Width of the counter and the output data bus

    Returns:
        The number of sub-transactions in the input transaction.
    """

    cnt = Uint[w_out](0)

    async for (data, eot) in din:
        if cnt_one_more:
            if all(eot[:cnt_lvl]):
                cnt += 1

        if all(eot):
            yield cnt

        if not cnt_one_more:
            if all(eot[:cnt_lvl]):
                cnt += 1
