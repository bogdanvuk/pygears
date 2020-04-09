from pygears.lib import trunc
from pygears.util.call import call
from pygears.typing import Ufixp, Fixp, Uint, Int


def test_ufixp():
    val = Ufixp[2, 4](2.25)
    q2_1 = Ufixp[2, 3]
    q1_2 = Ufixp[1, 3]
    q1_1 = Ufixp[1, 2]

    assert call(trunc, val, t=q2_1)[0] == 2.0
    assert call(trunc, val, t=q1_2)[0] == 0.25
    assert call(trunc, val, t=q1_1)[0] == 0.0


def test_fixp():
    val = Fixp[3, 5](-2.75)

    q2_1 = Fixp[3, 4]
    q1_2 = Fixp[2, 4]
    q1_1 = Fixp[2, 3]

    assert call(trunc, val, t=q2_1)[0] == -3.0
    assert call(trunc, val, t=q1_2)[0] == -0.75
    assert call(trunc, val, t=q1_1)[0] == -1.0


def test_uint():
    assert call(trunc, Uint[8](0xaa), t=Uint[7])[0] == 0x2a


def test_int():
    assert call(trunc, Int[8](-0x56), t=Int[7])[0] == -0x16
