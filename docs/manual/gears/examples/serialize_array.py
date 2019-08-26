from pygears.lib import check, drv, serialize
from pygears.typing import Uint, Array

drv(t=Array[Uint[8], 4], seq=[(1, 2, 3, 4), (5, 6, 7, 8)]) \
    | serialize \
    | check(ref=[[1, 2, 3, 4], [5, 6, 7, 8]])
