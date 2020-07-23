from pygears import gear
from pygears.sim import sim
from pygears.typing import Uint, Int, Fixp, Ufixp
from pygears.lib import directed, drv


def test_add_bin_uint():
    @gear(hdl={'compile': True})
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

    sim(timeout=8)


def test_add_bin_fixp():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield a + b
            yield b + a
            yield a + a
            yield b + b
            yield a + 2
            yield 2 + a
            yield b + 2
            yield 2 + b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[-0.125, -0.125, 15.75, -16.0, 9.875, 9.875, -6, -6])

    sim(timeout=8)


def test_sub_bin_uint():
    @gear(hdl={'compile': True})
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

    sim(timeout=8)


def test_sub_bin_fixp():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield a - b
            yield b - a
            yield a - a
            yield b - b
            yield a - 2
            yield 2 - a
            yield b - 2
            yield 2 - b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[15.875, -15.875, 0, 0, 5.875, -5.875, -10, 10])

    sim(timeout=8)
