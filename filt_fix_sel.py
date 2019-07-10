from pygears.lib import filt, drv, check
from pygears.typing import Union, Uint, Int

drv(t=Union[Uint[8], Int[8]], seq=[(1, 0), (2, 1), (3, 0), (4, 1), (5, 0)]) \
    | filt(fixsel=0) \
    | check(ref=[1, 3, 5])
