from pygears import gear
from pygears.lib import drv
from pygears.sim import sim, cosim
from pygears.typing import Queue, Uint
from pygears.lib import directed


def test_simple(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test,
             ref=[list(range(10))])

    cosim('/test', 'verilator')
    sim(tmpdir)
