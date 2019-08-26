from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[4], seq=[2, 5, 9])

(a // 3) | check(ref=[0, 1, 3])
