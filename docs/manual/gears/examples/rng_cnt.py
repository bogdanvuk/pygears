from pygears.cookbook import rng
from pygears.common import shred
from pygears.cookbook.verif import drv
from pygears.typing import Uint

drv(t=Uint[4], seq=[10]) | rng | shred
