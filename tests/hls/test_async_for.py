from pygears import gear
from pygears.lib import qrange
from pygears.lib import drv
from pygears.sim import sim
from pygears.typing import Queue, Uint
from pygears.lib import directed


def test_simple_async_sim(tmpdir, sim_cls):
    @gear(hdl={'compile': True})
    async def test() -> Uint[3]:
        async for i, _ in qrange(4):
            yield i

    directed(f=test(sim_cls=sim_cls), ref=list(range(4)) * 2)

    sim(tmpdir, timeout=8)

def test_simple(tmpdir, sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test(sim_cls=sim_cls),
             ref=[list(range(10))])

    sim(tmpdir)


def test_exit_cond(tmpdir, sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

        yield din.dtype.data(0), din.dtype.eot.max

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test(sim_cls=sim_cls),
             ref=[list(range(10)), [0]])

    sim(tmpdir)
