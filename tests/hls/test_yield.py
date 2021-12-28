from pygears import gear, sim
from pygears.typing import Uint
from pygears.lib import directed, drv


def test_two_alter_outs_const():
    @gear
    async def test() -> (Uint[4], Uint[4]):
        yield 0, None
        yield None, 1

    directed(f=test(__sim__='verilator'), ref=[[0, 0], [1, 1]])

    sim(timeout=4)


def test_two_alter_outs():
    @gear
    async def test(din) -> (Uint[4], Uint[4]):
        async with din as d:
            yield d, None

        async with din as d:
            yield None, d

    directed(drv(t=Uint[4], seq=[0, 1, 0, 1]), f=test(__sim__='verilator'), ref=[[0, 0], [1, 1]])

    sim(timeout=4)
