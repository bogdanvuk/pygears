from pygears.sim import sim, verif, drv, mon
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.seqr import seqr

from pygearslib.batch_active import batch_active
from pygears.typing import Queue, Uint
from pygears import gear

t_din = Queue[Uint[16]]


@gear
async def check(din, *, ret):
    val = await din.get()
    din.task_done()
    ret.append(val)


ret = []
seqr(t=t_din, seq=[list(range(10))]) \
    | drv \
    | batch_active(batch_size=2, sim_cls=SimSocket) \
    | mon \
    | check(ret=ret)

sim()

print(ret)
