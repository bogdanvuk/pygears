from pygears.lib import drv, check, czip
from pygears.typing import Queue, Uint

x = drv(t=Queue[Uint[5]], seq=[[10, 11, 12]])
y = drv(t=Queue[Uint[5]], seq=[[20, 21, 22]])

czip(x, y) | check(ref=[[(10, 20), (11, 21), (12, 22)]])
