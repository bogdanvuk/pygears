from pygears import Intf, bind, ErrReportLevel, gear, registry
from pygears.common import quenvelope
from pygears.typing import Queue, Uint, Tuple, TLM
from pygears.sim import sim, verif, drv
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.dtype_rnd_seq import dtype_rnd_seq
from pygears.sim.scv import create_type_cons
from pygears.cookbook.rng import rng
from pygears.core.gear import Gear
from pygears.sim.modules.socket import SimSocket

bind("ErrReportLevel", ErrReportLevel.debug)
registry("SimModuleNamespace")['Gear'] = SimSocket

t_cfg = Tuple[Uint[4], Uint[4], Uint[2]]
params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)


@gear
async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
              cnt_one_more) -> TLM[Queue[Uint[4]]]:
    cfg = await din.get()
    din.task_done()

    cfg = list(cfg)
    cfg[1] += 1
    yield list(range(*cfg))


seqr(t=t_cfg, seq=[(2, 6, 1), (2, 8, 2)]) \
    | drv \
    | rng(**params, sim_cls=SimSocket)

# report = verif(
#     seqr(t=t_cfg, seq=[(2, 6, 1)]),
#     f=rng(**params, sim_cls=SimSocket),
#     ref=ref(**params))

from pygears.util.print_hier import print_hier
print_hier()

sim()

# print(report)
# assert all(item['match'] for item in report)
