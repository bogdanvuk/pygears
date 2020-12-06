from pygears.lib import drv, check, mul, fmap
from pygears.typing import Queue, Uint

drv(t=Queue[Uint[16]], seq=[[0, 1, 2, 3, 4]]) \
    | fmap(f=mul(2)) \
    | check(ref=[[0, 2, 4, 6, 8]])
