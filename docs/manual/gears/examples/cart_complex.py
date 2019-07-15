from pygears.lib import drv, check, cart
from pygears.typing import Queue, Uint

real = drv(t=Queue[Uint[5]], seq=[[10, 11, 12]])
imag = drv(t=Uint[5], seq=[0])

cart(real, imag) | check(ref=[[(10, 0), (11, 0), (12, 0)]])
