from pygears import gear, reg
from pygears.lib import qrange
from pygears.lib import drv
from pygears.sim import sim, cosim
from pygears.typing import Queue, Uint
from pygears.lib import directed


def test_const_op():
    @gear(hdl={'compile': True})
    async def test() -> Uint[3]:
        yield 1 + 1
        yield 2 + 2
        yield 3 + 3

    # reg['results-dir'] = '/tools/home/tmp/const_add'
    directed(f=test(__sim__='verilator'), ref=[2, 4, 6])

    sim(timeout=3)


def test_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Uint[4]:
        async with din as d:
            yield 1 + d

        async with din as d:
            yield 2 + d

        async with din as d:
            yield 3 + d

    reg['results-dir'] = '/tools/home/tmp/hls_call'
    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim(timeout=3)


# test_op()
