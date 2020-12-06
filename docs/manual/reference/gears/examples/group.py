from pygears.lib import group, check, drv
from pygears.typing import Uint

size = drv(t=Uint[3], seq=[3, 4])

drv(t=Uint[4], seq=[1, 2, 3, 4, 5, 6, 7]) \
    | group(size=size) \
    | check(ref=[[1, 2, 3], [4, 5, 6, 7]])
