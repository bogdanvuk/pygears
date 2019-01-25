from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'svmod_fn': 'qlen_cnt.sv'})
# @gear(svgen={'compile': True})
async def qlen_cnt(din: Queue['tdin', 'din_lvl'],
                   *,
                   cnt_lvl=1,
                   cnt_one_more=False,
                   w_out=16) -> Uint['w_out']:
    '''Outputs only one value when input eots'''

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
