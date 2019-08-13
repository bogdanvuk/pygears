from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[4], seq=[0, 7, 15])

(-a) | check(ref=[0, -7, -15])
