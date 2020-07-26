from pygears import gear, reg
from pygears.sim import sim
from pygears.typing import Uint, Int, Fixp, Ufixp
from pygears.lib import directed, drv


def test_abs_fixp():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield abs(a)
            yield abs(b)

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[7.875, 8.0])

    sim()


def test_abs_int():
    @gear(hdl={'compile': True})
    async def test(a_i: Uint[6], b_i: Int[8]) -> Int[9]:
        async with a_i as a, b_i as b:
            yield abs(a)
            yield abs(b)

    directed(drv(t=Uint[6], seq=[Uint[6].max]),
             drv(t=Int[8], seq=[Int[8].min]),
             f=test(__sim__='verilator'),
             ref=[Uint[6].max, -Int[8].min])

    reg['debug/trace'] = ['*']
    sim(resdir='/tools/home/tmp/const_add/output')
