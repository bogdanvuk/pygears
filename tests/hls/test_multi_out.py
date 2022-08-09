from pygears import gear, GearDone
from pygears.typing import Uint
from pygears.lib import delay_rng, collect, drv
from pygears.sim import sim, cosim

@gear
async def dut(din) -> (Uint[8], ) * 3:
    async with din as d:
        yield d, d, None


d1, d2, d3 = drv(t=Uint[8], seq=[1, 2]) | dut

res1 = []
res2 = []
res3 = []

d1 | delay_rng(2, 2) | collect(result=res1)
d2 | collect(result=res2)
d3 | collect(result=res3)

cosim('/dut', 'verilator', outdir='/tmp/test_multi_out')
sim()

breakpoint()
