from pygears import gear
from pygears.typing import Uint, Tuple, Queue
from pygears.lib import cart_sync_with, ccat, gt, rng

TCfg = Tuple[{'period': Uint['w_period'], 'width': Uint['w_width']}]

@gear
def pulse(cfg: TCfg):
    """Generates pulse of variable length,
    width is clk cycles for value 0"""
    cnt = rng(0, cfg['period'], 1)
    width = (cfg | cart_sync_with(cnt))['width']
    dout = ccat(gt(cnt, width), cnt[1]) | Queue[Uint[1], 1]

    return dout
