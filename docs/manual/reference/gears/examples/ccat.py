from pygears.lib import drv, check, ccat
from pygears.typing import Uint

x = drv(t=Uint[5], seq=[10, 11, 12])
y = drv(t=Uint[5], seq=[20, 21, 22])

ccat(x, y) | check(ref=[(10, 20), (11, 21), (12, 22)])
