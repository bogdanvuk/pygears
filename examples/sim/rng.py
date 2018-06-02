from pygears import Intf, bind, ErrReportLevel, gear
from pygears.common import quenvelope
from pygears.typing import Queue, Uint, Tuple, TLM
from pygears.sim import sim, seq, verif
from pygears.cookbook.rng import rng

cons = {
    'vars': {
        'f0': 'unsigned',
        'f1': 'unsigned',
        'f2': 'unsigned',
    },
    'constraints':
    ['f0() < f1()', 'f0() < 16', 'f1() < 4', 'f2() < f1() - f0()', 'f2() > 0']
}

bind("ErrReportLevel", ErrReportLevel.debug)

t_cfg = Tuple[Uint[4], Uint[2], Uint[2]]
outdir = '/tmp/sim_test'
params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)


@gear
async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
              cnt_one_more) -> TLM[Queue[Uint[4]]]:
    cfg = await din.get()
    din.task_done()

    cfg = list(cfg)
    cfg[1] += 1
    yield list(range(*cfg))


report = verif(
    seq(t=t_cfg, cons=cons, outdir=outdir), f=rng(**params), ref=ref(**params))

from pygears.util.print_hier import print_hier
print_hier()

sim(outdir=outdir)

print(report)
assert all(item['match'] for item in report)
