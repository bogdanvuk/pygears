from pygears.lib import drv, check, cart
from pygears.typing import Queue, Uint

op1 = drv(t=Queue[Uint[5]], seq=[[10, 11, 12], [20, 21, 22]])
op2 = drv(t=Uint[1], seq=[0, 1])

cart(op1, op2) | check(ref=[[(10, 0), (11, 0), (12, 0)], [(20, 1), (21, 1), (22, 1)]])
