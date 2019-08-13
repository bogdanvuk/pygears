from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[4], seq=[0, 1, 2])
b = drv(t=Uint[4], seq=[0, 1, 2])

(a * b) | check(ref=[0, 1, 4])
