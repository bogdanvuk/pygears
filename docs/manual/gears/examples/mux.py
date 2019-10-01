from pygears.lib import check, mux, drv
from pygears.typing import Uint

ctrl = drv(t=Uint[2], seq=[0, 1, 2, 0, 1, 2])
a = drv(t=Uint[4], seq=[10, 11])
b = drv(t=Uint[5], seq=[20, 21])
c = drv(t=Uint[6], seq=[30, 31])

mux(ctrl, a, b, c) \
    | check(ref=[(10, 0), (20, 1), (30, 2), (11, 0), (21, 1), (31, 2)])
