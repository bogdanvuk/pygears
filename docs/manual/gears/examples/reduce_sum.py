from pygears.lib import drv, check, accum
from pygears.typing import Queue, Uint

drv(t=Queue[Uint[4]], seq=[[0, 1, 2, 3, 4]]) \
    | accum(init=Uint[8](0)) \
    | check(ref=[10])
