from pygears.lib import drv, check, rng, flatten
from pygears.typing import Uint

rng_vals = drv(t=Uint[4], seq=[6]) | rng | flatten
rng_vals_incr = rng_vals + 1

rng_vals_incr | check(ref=[1, 2, 3, 4, 5, 6])
