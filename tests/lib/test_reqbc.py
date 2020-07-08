from pygears import gear, reg
from pygears.lib.reqbc import reqbc
from pygears.lib import qrange, delay_rng, drv, collect
from pygears.typing import Unit
from pygears.sim import sim, cosim


@gear
def test(rd0, rd1):
    return reqbc(qrange(10), rd0, rd1)


d0, d1 = test(
    drv(t=Unit, seq=[Unit()] * 10) | delay_rng(2, 2),
    drv(t=Unit, seq=[Unit()] * 10) | delay_rng(1, 1),
)

res0 = []
res1 = []

d0 | collect(result=res0)
d1 | collect(result=res1)

reg['debug/trace'] = ['*']
cosim('/test', 'verilator', outdir='./output')
sim()

breakpoint()
