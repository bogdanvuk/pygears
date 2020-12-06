from pygears.lib import check, drv, serialize
from pygears.typing import Uint, Array

din = drv(t=Array[Uint[8], 4], seq=[(1, 2, 3, 4), (5, 6, 7, 8)])
active = drv(t=Uint[2], seq=[2, 3])

serialize(din, active) \
    | check(ref=[[1, 2], [5, 6, 7]])
