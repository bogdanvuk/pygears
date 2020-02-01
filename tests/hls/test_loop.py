from pygears import gear
from pygears.typing import Bool, Uint
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed
from pygears.lib.rng import qrange


def test_for_loop(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Uint) -> b'din':
        async with din as d:
            for i in range(d):
                yield i

    directed(drv(t=Uint[4], seq=[4, 2]),
             f=test,
             ref=list(range(4)) + list(range(2)))

    cosim('/test', 'verilator')
    sim(tmpdir)
