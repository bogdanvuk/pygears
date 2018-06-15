from pygears import gear, registry
from pygears.sim import sim, verif
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.print_hier import print_hier
from pygearslib.chop import chop

t_din = Queue[Uint[16]]
t_dout = Queue[Uint[16], 2]
t_cfg = Uint[16]

registry('SimConfig')['dbg_assert'] = False


@gear
async def chop_ref_model(din: Queue['TData'],
                         cfg: 'TCfg') -> b'Queue[TData, 2]':

    cfg_val = await cfg.get()
    for i in range(cfg_val):
        val = await din.get()
        yield val

        din.task_done()

    cfg.task_done()


seqrs = [seqr(t=t_din, seq=[list(range(10))]), seqr(t=t_cfg, seq=[10])]
report = verif(*seqrs, f=chop(sim_cls=SimSocket), ref=chop_ref_model)

print_hier()

sim(outdir='/tools/home/tmp')

print(report)
