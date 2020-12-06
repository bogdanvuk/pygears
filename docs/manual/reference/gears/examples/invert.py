from pygears.lib import drv, check
from pygears.typing import Uint

a = drv(t=Uint[8], seq=[0x01, 0x0f, 0xff])

(~a) | check(ref=[0xfe, 0xf0, 0x00])
