from pygears.lib import drv, check, clip
from pygears.typing import Uint, Queue

drv(t=Queue[Uint[4]], seq=[list(range(10))]) \
    | clip(size=Uint[4](6)) \
    | check(ref=[list(range(6)), list(range(6, 10))])
