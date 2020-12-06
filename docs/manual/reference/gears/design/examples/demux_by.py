from pygears.lib import check, demux, drv
from pygears.typing import Uint

ctrl = drv(t=Uint[2], seq=[0, 1, 2, 3])
outs = drv(t=Uint[4], seq=[10, 11, 12, 13]) \
    | demux(ctrl)

outs[0] | check(ref=[10])
outs[1] | check(ref=[11])
outs[2] | check(ref=[12])
outs[3] | check(ref=[13])
