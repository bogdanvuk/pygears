from pygears.lib import trunc
from pygears.util.call import call
from pygears.typing import Ufixp, Fixp, Uint, Int


def test_ufixp():
    val = Ufixp[2, 4](2.25)
    q2_1 = Ufixp[2, 3]
    q1_2 = Ufixp[1, 3]
    q1_1 = Ufixp[1, 2]
    q3_1 = Ufixp[3, 4]
    q1_3 = Ufixp[1, 4]

    assert call(trunc, val, t=q3_1)[0] == 2.0
    assert call(trunc, val, t=q1_3)[0] == 0.25
    assert call(trunc, val, t=q2_1)[0] == 2.0
    assert call(trunc, val, t=q1_2)[0] == 0.25
    assert call(trunc, val, t=q1_1)[0] == 0.0


def test_fixp():
    val = Fixp[3, 5](-2.75)

    q2_1 = Fixp[3, 4]
    q1_2 = Fixp[2, 4]
    q1_1 = Fixp[2, 3]
    q5_1 = Fixp[6, 7]
    q1_5 = Fixp[2, 7]

    assert call(trunc, val, t=q2_1)[0] == -3.0
    assert call(trunc, val, t=q1_2)[0] == -0.75
    assert call(trunc, val, t=q1_1)[0] == -1.0
    assert call(trunc, val, t=q5_1)[0] == -3.0
    assert call(trunc, val, t=q1_5)[0] == -0.75

    val = Fixp[3, 5](0.75)
    assert call(trunc, val, t=Fixp[0, 2])[0] == 0.25


def test_uint():
    assert call(trunc, Uint[8](0xaa), t=Uint[7])[0] == 0x2a
    assert call(trunc, Uint[8](0xaa), t=Uint[9])[0] == 0xaa


def test_int():
    assert call(trunc, Int[8](-0x56), t=Int[7])[0] == -0x16
    assert call(trunc, Int[8](-0x56), t=Int[15])[0] == -0x56
