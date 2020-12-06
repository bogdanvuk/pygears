from pygears.lib import drv, check, cart_sync
from pygears.typing import Queue, Uint

op1 = drv(t=Queue[Uint[5]], seq=[[10, 11, 12], [20, 21, 22]])
op2 = drv(t=Uint[1], seq=[0, 1])

out1, out2 = cart_sync(op1, op2)
out1 | check(ref=[[10, 11, 12], [20, 21, 22]])
out2 | check(ref=[0, 0, 0, 1, 1, 1])
