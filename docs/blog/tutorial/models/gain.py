from pygears import gear, config
from pygears.typing import Ufixp, Uint
from pygears.lib import drv, collect
from pygears.sim import sim


config['trace/level'] = 0

@gear
def darken(din: Uint[8], *, gain) -> Ufixp[1, 8]:
    res = din * Ufixp[0, 8](gain)
    return res | Uint[8]


res = []
drv(t=Uint[8], seq=[255, 128, 0]) \
    | darken(gain=0.5) \
    | int \
    | collect(result=res)

sim()

print(res)
