from pygears.typing import Ufixp, qround, Bool, Fixp, Uint, Int
from pygears.typing.qround import qround_even


def test_basic():
    assert qround(Fixp[6, 10](-1.5 - 0.0625)) == Int[7](-2.0)
    assert qround(Fixp[6, 10](-1.5)) == Int[7](-1.0)

    assert qround(Fixp[6, 10](-0.5 - 0.0625)) == Int[7](-1.0)
    assert qround(Fixp[6, 10](-0.5)) == Int[7](0.0)

    assert qround(Ufixp[6, 10](2.5)) == Uint[7](3.0)

    assert qround(Ufixp[6, 10](2.375)) == Uint[7](2.0)

    assert qround(Ufixp[6, 10](3.5)) == Uint[7](4.0)

    assert qround(Ufixp[3, 6](0.25), 1) == Ufixp[4, 5](0.5)


def test_qround_even():
    assert qround_even(Fixp[6, 10](-1.5)) == Int[7](-2.0)
    assert qround_even(Fixp[6, 10](-1.5 + 0.0625)) == Int[7](-1.0)

    assert qround_even(Fixp[6, 10](-0.5)) == Int[7](0.0)
    assert qround_even(Fixp[6, 10](-0.5 - 0.0625)) == Int[7](-1.0)

    assert qround_even(Ufixp[6, 10](0.5)) == Uint[7](0.0)
    assert qround_even(Ufixp[6, 10](0.5 + 0.0625)) == Uint[7](1.0)

    assert qround_even(Ufixp[6, 10](1.5 - 0.0625)) == Uint[7](1.0)
    assert qround_even(Ufixp[6, 10](1.5)) == Uint[7](2.0)
