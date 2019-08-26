from pygears.lib import drv, check, sub, fmap
from pygears.typing import Int, Uint, Union

drv(t=Union[Int[16], Uint[16]], seq=[(0, 1), (1, 1), (-10, 0), (-11, 0)]) \
    | fmap(f=(sub(b=1), None)) \
    | check(ref=[(0, 1), (1, 1), (-11, 0), (-12, 0)])
