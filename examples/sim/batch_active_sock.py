from pygears import gear
from pygears.sim import drv, mon, sim, verif
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
# from pygearslib.batch_active import batch_active
from pygears.typing import Queue, Uint

t_din = Queue[Uint[16]]


@gear
def dut(din: Queue[Uint['dinw']]) -> Queue[Uint['dinw']]:
    pass


@gear
async def check(din, *, ret):
    val = await din.get()
    din.task_done()
    ret.append(val)


ret = []
seqr(t=t_din, seq=[list(range(10))]) \
    | drv \
    | dut(sim_cls=SimSocket) \
    | mon \
    | check(ret=ret)

sim()

print(ret)
