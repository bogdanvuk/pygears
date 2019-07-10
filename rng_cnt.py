from pygears.lib import rng
from pygears.lib import shred
from pygears.lib.verif import drv
from pygears.typing import Uint

drv(t=Uint[4], seq=[10]) | rng | shred
