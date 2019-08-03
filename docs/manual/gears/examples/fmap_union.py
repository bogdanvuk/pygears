from pygears.lib import drv, check, sub, fmap
from pygears.typing import Uint, Tuple, Int, Union

drv(t=Union[Uint[16], Int[16]], seq=[(0, 0), (1, 0), (-10, 1), (-11, 1)]) \
    | fmap(f=(None, sub(b=1))) \
    | check(ref=[(0, 0), (1, 0), (-11, 1), (-12, 1)])
