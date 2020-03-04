from pygears import gear
from pygears.util.call import call
from pygears import config
from pygears.lib import drv, collect
from pygears.sim import sim, cosim
from pygears.typing import Tuple, Uint, Queue
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


def test_exit_cond(tmpdir):

    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

        yield din.dtype.data(0), din.dtype.eot.max

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test,
             ref=[list(range(10)), [0]])

    cosim('/test', 'verilator')
    sim(tmpdir)
