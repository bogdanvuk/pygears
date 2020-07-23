from pygears import gear
from pygears.sim import sim
from pygears.typing import Uint, Int, Fixp, Ufixp
from pygears.lib import directed, drv


def test_mul_bin_uint():
    @gear(hdl={'compile': True})
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


def test_mul_bin_fixp():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[8, 16]:
        async with a_i as a, b_i as b:
            yield a * b
            yield b * a
            yield a * a
            yield b * b
            yield a * 2
            yield 2 * a
            yield b * 2
            yield 2 * b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[-63.0, -63.0, 62.015625, 64.0, 15.75, 15.75, -16, -16])

    sim(timeout=8)
