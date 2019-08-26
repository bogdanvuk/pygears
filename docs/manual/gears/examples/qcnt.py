from pygears.lib import qcnt, check, drv
from pygears.typing import Uint, Queue

drv(t=Queue[Uint[4]], seq=[[1, 2, 3, 4, 5]]) \
    | qcnt \
    | check(ref=[5])
