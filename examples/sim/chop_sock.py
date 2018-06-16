from pygears import gear, registry
from pygears.sim import sim, verif, drv
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

seqrs = [seqr(t=t_din, seq=[list(range(10))]), seqr(t=t_cfg, seq=[10])]

# seqrs[0] | drv
stim = tuple(s | drv for s in seqrs)
stim | chop | shred

# report = verif(*seqrs, f=chop(sim_cls=SimSocket), ref=chop_ref_model)

print_hier()

sim(outdir='/tools/home/tmp')

# print(report)
