from pygears import gear, datagear, reg
from pygears.sim import sim
from pygears.typing import Uint
from pygears.lib import directed


def test_const_args_gear():
    @gear
    async def func(dina, dinb) -> b'Uint[2] * dina + dinb':
        async with dina as a, dinb as b:
            yield 2 * a + b

    @gear
    async def test() -> Uint[5]:
        async with func(1, 4) as v:
            yield v

        async with func(2, 5) as v:
            yield v

        async with func(3, 6) as v:
            yield v

    directed(f=test(), ref=[6, 9, 12] * 10)
    sim(timeout=3 * 10)
