import pytest

from pygears import find, Intf
from pygears.lib import drv, check
from pygears.typing import Uint, Int, Unit
from pygears.sim import sim
from pygears.util.test_utils import synth_check


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


def test_shift_complete():
    res = Intf(Uint[8]) >> 8
    assert res.dtype == Unit

    res = Intf(Int[8]) >> 8
    assert res.dtype == Unit


@pytest.mark.xfail(raises=TypeError)
def test_shift_larger():
    Intf(Uint[8]) >> 9


@synth_check({'logic luts': 0, 'ffs': 0}, tool='yosys', freduce=True)
def test_shr_synth():
    Intf(Uint[8]) >> 4
