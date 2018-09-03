from pygears import gear
from pygears.typing import Queue, Uint


@gear(svgen={'svmod_fn': 'qlen_cnt.sv'})
async def qlen_cnt(din: Queue['tdin', 'din_lvl'],
                   *,
                   cnt_lvl=1,
                   cnt_one_more=False,
                   w_out=16) -> Uint['w_out']:
    '''Outputs only one value when input eots'''
    pass
