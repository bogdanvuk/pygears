from pygears import gear
from pygears.sim import sim
from pygears.typing import Int, Uint
from pygears.lib import directed, drv


def test_abs_int():
    @gear
    async def test(a_i: Uint[6], b_i: Int[8]) -> Int[9]:
        async with a_i as a, b_i as b:
            yield abs(a)
            yield abs(b)

    directed(drv(t=Uint[6], seq=[Uint[6].max]),
             drv(t=Int[8], seq=[Int[8].min]),
             f=test(__sim__='verilator'),
             ref=[Uint[6].max, -Int[8].min])

    sim()


def test_add_bin_uint():
    @gear
    async def test(a_i: Uint[3], b_i: Int[4]) -> Int[6]:
        async with a_i as a, b_i as b:
            yield a + b
            yield b + a
            yield a + a
            yield b + b
            yield a + 2
            yield 2 + a
            yield b + 2
            yield 2 + b

    directed(drv(t=Uint[3], seq=[7]),
             drv(t=Int[4], seq=[-7]),
             f=test(__sim__='verilator'),
             ref=[0, 0, 14, -14, 9, 9, -5, -5])

    sim()


def test_and_bin_uint():
    @gear
    async def test(a_i: Uint[3], b_i: Int[4]) -> Int[5]:
        async with a_i as a, b_i as b:
            yield a & b
            yield b & a
            yield a & a
            yield b & b
            yield a & 0x5
            yield 0x5 & a
            yield b & 0x5
            yield 0x5 & b

    directed(drv(t=Uint[3], seq=[7]),
             drv(t=Int[4], seq=[-7]),
             f=test(__sim__='verilator'),
             ref=[0x1, 0x1, 0x7, -7, 0x5, 0x5, 0x1, 0x1])

    sim(timeout=8)


def test_mul_bin_uint():
    @gear
    async def test(a_i: Uint[3], b_i: Int[4]) -> Int[8]:
        async with a_i as a, b_i as b:
            yield a * b
            yield b * a
            yield a * a
            yield b * b
            yield a * 2
            yield 2 * a
            yield b * 2
            yield 2 * b

    directed(drv(t=Uint[3], seq=[7]),
             drv(t=Int[4], seq=[-7]),
             f=test(__sim__='verilator'),
             ref=[-49, -49, 49, 49, 14, 14, -14, -14])

    sim(timeout=8)


def test_sub_bin_uint():
    @gear
    async def test(a_i: Uint[3], b_i: Int[4]) -> Int[6]:
        async with a_i as a, b_i as b:
            yield a - b
            yield b - a
            yield a - a
            yield b - b
            yield a - 2
            yield 2 - a
            yield b - 2
            yield 2 - b

    directed(drv(t=Uint[3], seq=[7]),
             drv(t=Int[4], seq=[-7]),
             f=test(__sim__='verilator'),
             ref=[14, -14, 0, 0, 5, -5, -9, 9])

    sim()
