from pygears.typing import Ufixp, qround, Bool, Fixp
from pygears.typing.qround import qround_even


def test_basic():
    assert qround(Fixp[6, 10](-1.5 - 0.0625)) == Fixp[7, 7](-2.0)
    assert qround(Fixp[6, 10](-1.5)) == Fixp[7, 7](-1.0)

    assert qround(Fixp[6, 10](-0.5 - 0.0625)) == Fixp[7, 7](-1.0)
    assert qround(Fixp[6, 10](-0.5)) == Fixp[7, 7](0.0)

    assert qround(Ufixp[6, 10](2.5)) == Ufixp[7, 7](3.0)

    assert qround(Ufixp[6, 10](2.375)) == Ufixp[7, 7](2.0)

    assert qround(Ufixp[6, 10](3.5)) == Ufixp[7, 7](4.0)

    assert qround(Ufixp[3, 6](0.25), 1) == Ufixp[4, 5](0.5)


def test_qround_even():
    assert qround_even(Fixp[6, 10](-1.5)) == Fixp[7, 7](-2.0)
    assert qround_even(Fixp[6, 10](-1.5 + 0.0625)) == Fixp[7, 7](-1.0)

    assert qround_even(Fixp[6, 10](-0.5)) == Fixp[7, 7](0.0)
    assert qround_even(Fixp[6, 10](-0.5 - 0.0625)) == Fixp[7, 7](-1.0)

    assert qround_even(Ufixp[6, 10](0.5)) == Ufixp[7, 7](0.0)
    assert qround_even(Ufixp[6, 10](0.5 + 0.0625)) == Ufixp[7, 7](1.0)

    assert qround_even(Ufixp[6, 10](1.5 - 0.0625)) == Ufixp[7, 7](1.0)
    assert qround_even(Ufixp[6, 10](1.5)) == Ufixp[7, 7](2.0)
