from pygears.lib import drv, check, chop
from pygears.typing import Uint, Queue

drv(t=Queue[Uint[4]], seq=[list(range(10))]) \
    | chop(size=4) \
    | check(ref=[list(range(4)), list(range(4, 8)), list(range(8, 10))])
