from pygears.lib import drv, check, cart
from pygears.typing import Queue, Uint

x = drv(t=Queue[Uint[5]], seq=[[10, 11, 12]])
y = drv(t=Uint[5], seq=[0])

cart(x, y) | check(ref=[[(10, 0), (11, 0), (12, 0)]])
