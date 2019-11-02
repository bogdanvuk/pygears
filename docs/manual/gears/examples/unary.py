from pygears.lib import drv, check, unary
from pygears.typing import Uint

drv(t=Uint[4], seq=[0, 1, 2, 3, 4, 5, 6, 7, 8]) \
    | unary \
    | check(ref=[0x00, 0x01, 0x03, 0x07, 0x0f, 0x1f, 0x3f, 0x7f, 0xff])
