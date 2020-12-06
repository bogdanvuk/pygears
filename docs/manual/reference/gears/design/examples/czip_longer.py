from pygears.lib import drv, check, czip
from pygears.typing import Queue, Uint

x = drv(t=Queue[Uint[5]], seq=[[10, 11], [13, 14, 15]])
y = drv(t=Queue[Uint[5]], seq=[[20, 21, 22], [23, 24]])

czip(x, y) | check(ref=[[(10, 20), (11, 22)], [(13, 23), (15, 24)]])
