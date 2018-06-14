from pygears.sim import sim, verif, drv
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.seqr import seqr

from pygearslib.batch_active import batch_active
from pygears.typing import Queue, Uint

t_din = Queue[Uint[16]]

seqr(t=t_din, seq=[list(range(10))]) \
    | drv \
    | batch_active(batch_size=2, sim_cls=SimSocket)

sim()
