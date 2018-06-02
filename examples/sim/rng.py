from pygears import Intf, bind, ErrReportLevel, gear
from pygears.common import quenvelope
from pygears.typing import Queue, Uint, Tuple, TLM
from pygears.sim import sim, verif
from pygears.sim.modules.dtype_rnd_seq import dtype_rnd_seq
from pygears.sim.scv import create_type_cons
from pygears.cookbook.rng import rng

bind("ErrReportLevel", ErrReportLevel.debug)

t_cfg = Tuple[Uint[4], Uint[4], Uint[2]]
outdir = '/tmp/sim_test'
params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)

from pygears.svgen import svgen
@gear
def func(din, channeled) -> Tuple['din', 'channeled']:
    pass

@gear
def hier(din, *, f):
    return din | f

hier(Intf(Uint[2]), f=func(channeled=Intf(Uint[1])))
svgen(outdir=outdir)

# cons = create_type_cons(
#     t_cfg, scale=Uint[4], cons=['scale > 0', 'f1 > f0', 'f1 - f0 == scale*f2'])

# @gear
# async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
#               cnt_one_more) -> TLM[Queue[Uint[4]]]:
#     cfg = await din.get()
#     din.task_done()

#     cfg = list(cfg)
#     cfg[1] += 1
#     yield list(range(*cfg))

# report = verif(
#     dtype_rnd_seq(t=t_cfg, cons=cons), f=rng(**params), ref=ref(**params))

# from pygears.util.print_hier import print_hier
# print_hier()

# sim(outdir=outdir)

# print(report)
# assert all(item['match'] for item in report)
