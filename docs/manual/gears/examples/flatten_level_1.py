from pygears.lib import check, drv, flatten
from pygears.typing import Uint, Queue

drv(t=Queue[Uint[4]], seq=[[0, 1, 2]]) \
    | flatten \
    | check(ref=[0, 1, 2])
