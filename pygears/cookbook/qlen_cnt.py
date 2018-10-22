from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'svmod_fn': 'qlen_cnt.sv'})
async def qlen_cnt(din: Queue['tdin', 'din_lvl'],
                   *,
                   cnt_lvl=1,
                   cnt_one_more=False,
                   w_out=16) -> Uint['w_out']:
    '''Outputs only one value when input eots'''

    cnt = 0
    val = din.dtype((0, 0))

    while not all(val.eot):
        async with din as val:
            if all(val.eot[:cnt_lvl]):
                cnt += 1

    if not cnt_one_more:
        cnt -= 1
    yield cnt
