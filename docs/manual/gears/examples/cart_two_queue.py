from pygears.lib import drv, check, cart, shred
from pygears.typing import Queue, Uint

op1 = drv(t=Queue[Uint[5]], seq=[[10, 11], [20, 21], [30, 31]])
op2 = drv(t=Queue[Uint[5]], seq=[[10, 11, 12]])

cart(op1, op2) | check(ref=[[[(10, 10), (11, 10)], [(20, 11), (21, 11)], [(30, 12), (31, 12)]]])
