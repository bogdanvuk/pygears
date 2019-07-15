from pygears.lib import drv, check
from pygears.typing import Uint

op1 = drv(t=Uint[4], seq=[0, 1, 2])
op2 = drv(t=Uint[4], seq=[0, 1, 2])

(op1 + op2) | check(ref=[0, 2, 4])
