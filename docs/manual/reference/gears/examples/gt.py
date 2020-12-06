from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[4], seq=[1, 2, 3, 4, 5])
b = drv(t=Uint[4], seq=[4, 4, 4, 4, 4])

(a > b) | check(ref=[False, False, False, False, True])
