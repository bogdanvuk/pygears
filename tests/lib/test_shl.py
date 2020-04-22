from pygears import find
from pygears.lib import drv, check
from pygears.typing import Uint, Int
from pygears.sim import sim


def test_uint(cosim_cls):
    res = drv(t=Uint[4], seq=[0xa, 0xb, 0xc, 0xd]) << 4
    assert res.dtype == Uint[8]

    res | check(ref=[0xa0, 0xb0, 0xc0, 0xd0])

    find('/shl').params['sim_cls'] = cosim_cls
    sim()


def test_int(sim_cls):
    res = drv(t=Int[5], seq=[-0xa, -0xb, -0xc, -0xd]) << 4
    assert res.dtype == Int[9]

    res | check(ref=[-0xa0, -0xb0, -0xc0, -0xd0])

    find('/shl').params['sim_cls'] = sim_cls
    sim()
