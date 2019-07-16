from pygears import find
from pygears.lib import drv, check
from pygears.typing import Uint, Int
from pygears.sim import sim


def test_uint(tmpdir, sim_cls):
    res = drv(t=Uint[8], seq=[0xa1, 0xa2, 0xa3, 0xa4]) >> 4
    assert res.dtype == Uint[4]

    res | check(ref=[0xa] * 4)

    find('/shr').params['sim_cls'] = sim_cls
    sim(tmpdir)


def test_int(tmpdir, sim_cls):
    res = drv(t=Int[9], seq=[-0xa1, -0xa2, -0xa3, -0xa4]) >> 4
    assert res.dtype == Int[5]

    res | check(ref=[-0xb] * 4)

    find('/shr').params['sim_cls'] = sim_cls
    sim(tmpdir)


def test_int_logical(tmpdir, sim_cls):
    inp = drv(t=Int[9], seq=[-0xa1, -0xa2, -0xa3, -0xa4])

    res = (inp | Uint) >> 4
    res | check(ref=[(-0xa1 & 0x1ff) >> 4] * 4)

    find('/shr').params['sim_cls'] = sim_cls
    sim(tmpdir)
