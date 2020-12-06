from pygears.lib import qinterlace, check, drv
from pygears.typing import Uint, Queue

di1 = drv(t=Queue[Uint[4], 1], seq=[[1, 2], [3, 4]])
di2 = drv(t=Queue[Uint[4], 1], seq=[[5, 6], [7, 8]])

qinterlace(di1, di2) \
    | check(ref=[[[1, 2], [5, 6]], [[3, 4], [7, 8]]])
