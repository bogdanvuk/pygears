from pygears.lib import take, check, drv
from pygears.typing import Uint, Queue

size = drv(t=Uint[2], seq=[2, 3])

drv(t=Queue[Uint[4]], seq=[[1, 2, 3, 4], [1, 2, 3, 4]]) \
    | take(size=size) \
    | check(ref=[[1, 2], [1, 2, 3]])
