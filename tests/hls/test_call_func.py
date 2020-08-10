from pygears import gear, datagear, reg
from pygears.sim import sim
from pygears.typing import Uint
from pygears.lib import directed, drv


# TODO: Test really that the func was inlined
def test_const_args():
    def func(a, b):
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        yield func(1, 4)
        yield func(2, 5)
        yield func(3, 6)

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12] * 3)

    sim(timeout=3 * 3)


def test_const_args_datagear_as_gear():
    @datagear
    def func(a, b) -> b'Uint[2] * a + b':
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        async with func(1, 4) as v:
            yield v

        async with func(2, 5) as v:
            yield v

        async with func(3, 6) as v:
            yield v

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12] * 3)
    sim(timeout=3 * 3)


def test_const_args_gear():
    @gear(hdl={'compile': True})
    async def func(dina, dinb) -> b'Uint[2] * dina + dinb':
        async with dina as a, dinb as b:
            yield 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        async with func(1, 4) as v:
            yield v

        async with func(2, 5) as v:
            yield v

        async with func(3, 6) as v:
            yield v

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12] * 3)
    sim(timeout=3 * 3)


def test_call_inside_loop():
    @datagear
    def func(a, b) -> b'Uint[2] * a + b':
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[5]:
        for i in range(3):
            async with func(i, i) as v:
                yield v

    directed(f=test(__sim__='verilator'), ref=[0, 3, 6] * 3)
    sim(timeout=3 * 3)


def test_expr_args():
    @datagear
    def func(a, b) -> b'Uint[2] * a + b':
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test() -> Uint[8]:
        for i in range(3):
            async with func(2 * i + 1, (i << 2)) as v:
                yield v

    directed(f=test(__sim__='verilator'), ref=[2, 10, 18] * 3)
    sim(timeout=3 * 3)


def test_input_intf_arg():
    @datagear
    def func(a, b) -> b'Uint[2] * a + b':
        return 2 * a + b

    @gear(hdl={'compile': True})
    async def test(din: Uint[2]) -> Uint[8]:
        async with func(din, 2) as v:
            yield v

    directed(drv(t=Uint[2], seq=list(range(3)) * 3), f=test(__sim__='verilator'), ref=[2, 4, 6] * 3)
    sim(timeout=3 * 3)
