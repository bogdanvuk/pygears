from pygears.lib import rom, check, drv
from pygears.typing import Uint

drv(t=Uint[3], seq=[0, 1, 2, 3, 4, 5]) \
    | rom(data={1: 11, 3: 13, 5: 15}, dflt=10, dtype=Uint[4]) \
    | check(ref=[10, 11, 10, 13, 10, 15])
