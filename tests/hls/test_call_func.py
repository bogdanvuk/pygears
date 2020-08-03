from pygears import gear, datagear, reg
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


# # TODO: Test really that the func was inlined
# def test_const_args_datagear_as_func():
#     @datagear
#     def func(a, b):
#         return 2 * a + b

#     @gear(hdl={'compile': True})
#     async def test() -> Uint[5]:
#         yield func(1, 4)
#         yield func(2, 5)
#         yield func(3, 6)

#     directed(f=test(__sim__='verilator'), ref=[6, 9, 12])

#     sim(timeout=3)


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

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12] * 5)
    sim(timeout=3 * 5)


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

    directed(f=test(__sim__='verilator'), ref=[6, 9, 12] * 100)
    sim(timeout=3 * 100)


# reg['gear/memoize'] = True
# test_const_args_gear()
