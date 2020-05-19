from pygears import gear
from pygears.typing import Ufixp, Uint
from pygears.lib import drv, collect
from pygears.sim import sim


@gear
def darken(din: Uint[8], *, gain) -> Uint[8]:
    return din * Ufixp[0, 8](gain)


res = []
drv(t=Uint[8], seq=[255, 128, 0]) \
    | darken(gain=0.5) \
    | collect(result=res)

sim()

print(res)
