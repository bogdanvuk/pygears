from pygears.lib import replicate, check, drv
from pygears.typing import Uint

drv(t=Uint[4], seq=[5]) \
    | replicate(4) \
    | check(ref=[[5, 5, 5, 5]])
