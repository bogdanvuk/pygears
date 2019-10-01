from pygears.lib import check, mux, drv
from pygears.typing import Uint, Tuple

ctrl = drv(t=Uint[2], seq=[0, 1, 2])

drv(t=Tuple[Uint[4], Uint[5], Uint[6]], seq=[(10, 20, 30), (11, 21, 31), (12, 22, 32)]) \
    | mux(ctrl) \
    | check(ref=[(10, 0), (21, 1), (32, 2)])
