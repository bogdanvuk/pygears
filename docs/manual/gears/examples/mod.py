from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[4], seq=[0, 2, 4, 6, 8])

(a % 3) | check(ref=[0, 2, 1, 0, 2])
