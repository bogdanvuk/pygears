from pygears import gear, registry, GearDone
from pygears.sim import sim, verif, drv, mon, sim_assert
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.print_hier import print_hier
from pygears.cookbook.chop import chop
from pygears.common import shred

t_din = Queue[Uint[16]]
t_dout = Queue[Uint[16], 2]
t_cfg = Uint[16]

registry('SimConfig')['dbg_assert'] = False

seqrs = [
    seqr(t=t_din, seq=[list(range(9)), list(range(3))]),
    seqr(t=t_cfg, seq=[2, 3])
]


@gear
async def check(din, *, ref):
    try:
        items = []
        while (1):
            items.append(await din.get())

    finally:
        print(ref)
        sim_assert(items == ref)


# seqrs[0] | drv
stim = tuple(s | drv for s in seqrs)
stim | chop | mon | check(
    ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

# report = verif(*seqrs, f=chop(sim_cls=SimSocket), ref=chop_ref_model)

print_hier()

sim(outdir='/tools/home/tmp')

# print(report)
