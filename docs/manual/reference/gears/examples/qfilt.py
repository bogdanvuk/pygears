from pygears import datagear
from pygears.lib import filt, drv, check
from pygears.typing import Queue, Uint, Bool


@datagear
def even(x: Uint) -> Bool:
    return not x[0]


drv(t=Queue[Uint[8]], seq=[list(range(10))]) \
    | filt(f=even) \
    | check(ref=[list(range(0, 10, 2))])
