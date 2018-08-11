from pygears.sim import sim
from pygears.cookbook.verif import directed
from pygears.sim.modules.seqr import seqr
from pygears.typing import Queue, Uint
from pygears.util.print_hier import print_hier
from pygears.cookbook.chop import chop

t_din = Queue[Uint[16]]
t_dout = Queue[Uint[16], 2]
t_cfg = Uint[16]

seqrs = [
    seqr(t=t_din, seq=[list(range(9)), list(range(3))]),
    seqr(t=t_cfg, seq=[2, 3])
]


directed(
    *seqrs, f=chop, ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

print_hier()

sim()

# print(report)
