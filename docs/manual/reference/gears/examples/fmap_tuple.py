from pygears.lib import drv, check, mul, fmap
from pygears.typing import Uint, Tuple

drv(t=Tuple[Uint[16], Uint[16]], seq=[(0, 0), (1, 10), (2, 20)]) \
    | fmap(f=(mul(2), mul(2))) \
    | check(ref=[(0, 0), (2, 20), (4, 40)])
