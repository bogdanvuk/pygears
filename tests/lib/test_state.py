from pygears.lib import delay, directed, state
from pygears import gear, GearDone
from pygears.typing import Uint, Unit
from pygears.sim import clk, sim, cosim


def test_hold():
    @gear
    async def wr_sequence() -> Uint[4]:
        for i in range(4):
            yield i + 1
            await clk()
            await clk()
            await clk()

        raise GearDone

    @gear
    async def rd_sequence() -> Unit:
        for i in range(4):
            yield Unit()
            await clk()
            await clk()

        raise GearDone

    directed(
        wr_sequence(),
        rd_sequence(),
        f=state(hold=True),
        ref=[0, 2, 3, 4],
        delays=[delay(2)])

    cosim('/state', 'verilator')
    sim()
