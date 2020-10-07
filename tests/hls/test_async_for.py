from pygears import gear
from pygears.lib import qrange
from pygears.lib import drv
from pygears.sim import sim
from pygears.typing import Queue, Uint, Tuple
from pygears.lib import directed


def test_simple_async_sim(sim_cls):
    @gear(hdl={'compile': True})
    async def test() -> Uint[3]:
        async for i, _ in qrange(4):
            yield i

    directed(f=test(sim_cls=sim_cls), ref=list(range(4)) * 2)

    sim(timeout=8)

# TODO: This won't work ("for" instead of "async for"), throw reasonable error
# def test_simple_async_sim(sim_cls):
#     @gear(hdl={'compile': True})
#     async def test() -> Uint[3]:
#         for i, _ in qrange(4):
#             yield i

#     directed(f=test(sim_cls=sim_cls), ref=list(range(4)) * 2)

#     sim(timeout=8)


def test_simple(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test(sim_cls=sim_cls),
             ref=[list(range(10))])

    sim()


def test_exit_cond(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> b'din':
        async for (data, eot) in din:
            yield data, eot

        yield din.dtype.data(0), din.dtype.eot.max

    directed(drv(t=Queue[Uint[4]], seq=[list(range(10))]),
             f=test(sim_cls=sim_cls),
             ref=[list(range(10)), [0]])

    sim()


# Tests the issue where cycles were lost between the calls to qrange-s in simulation
def test_nested(sim_cls):
    @gear(hdl={'compile': True})
    async def test() -> Tuple[Uint[4], Uint[4]]:
        async for (i, i_eot) in qrange(2):
            async for (j, j_eot) in qrange(2):
                yield i, j

    directed(
        f=test(sim_cls=sim_cls),
        ref=[(i, j) for i in range(2) for j in range(2)] * 4,
    )

    sim(timeout=16)
