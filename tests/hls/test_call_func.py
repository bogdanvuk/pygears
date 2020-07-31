from pygears import gear, datagear
from pygears.sim import sim
from pygears.typing import Uint
from pygears.lib import directed


# TODO: Test really that the func was inlined
def test_const_args():
    def func(a, b):
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        yield func(1, 4)
        yield func(2, 5)
        yield func(3, 6)

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12])

    sim(timeout=3)


# TODO: Test really that the func was inlined
def test_const_args_datagear():
    @datagear
    def func(a, b):
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        yield func(1, 4)
        yield func(2, 5)
        yield func(3, 6)

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12])

    sim(timeout=3)

test_const_args_datagear()
