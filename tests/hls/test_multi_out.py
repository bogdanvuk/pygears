from pygears import gear, GearDone
from pygears.typing import Uint
from pygears.lib import delay_rng, drv, check
from pygears.sim import sim, cosim


def test_multi_out():
    @gear
    async def dut(din) -> (Uint[8], ) * 3:
        async with din as d:
            yield d, d, None

    d1, d2, d3 = drv(t=Uint[8], seq=[1, 2]) | dut

    d1 | delay_rng(2, 2) | check(ref=[1, 2])
    d2 | check(ref=[1, 2])
    d3 | check(ref=[])

    cosim('/dut', 'verilator')
    sim()
