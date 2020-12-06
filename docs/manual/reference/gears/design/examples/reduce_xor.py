from pygears.lib import reduce, drv, check
from pygears.typing import Queue, Uint

drv(t=Queue[Uint[8]], seq=[[0xff, 0xff, 0xff, 0xff]]) \
    | reduce(init=Uint[8](0), f=lambda x, y: x ^ y) \
    | check(ref=[0])
