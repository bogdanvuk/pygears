from pygears.lib import reduce, drv, check
from pygears.typing import Queue, Uint

(drv(t=Queue[Uint[8]], seq=[[0, 1, 0, 1, 0, 1, 0]]),
 drv(t=Uint[8], seq=[1])) \
    | reduce(f=lambda x, y: (x << 1) | y) \
    | check(ref=[0xaa])
