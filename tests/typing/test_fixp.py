import pytest
from math import floor
from pygears.typing import Fixp, Ufixp, typeof, Number, Int, Uint, div
from pygears.typing import get_match_conds


def test_fixp_is_number():
    get_match_conds(Fixp[1, 2], Number)


def test_float():
    t_a = Ufixp[2, 3]
    t_b = Fixp[3, 4]

    assert (t_a.decode(7) == t_a(3.5))
    assert (t_b.decode(-8) == t_b(-4.0))


def test_unsigned_add():
    t_a = Ufixp[2, 3]
    t_b = Ufixp[3, 4]

    assert (t_a + t_b == Ufixp[4, 5])

    a = t_a(3.5)
    b = t_b(7.5)
    assert a + b == Ufixp[4, 5](11.0)


def test_signed_add():
    t_a = Fixp[3, 4]
    t_b = Fixp[4, 5]

    assert (t_a + t_b == Fixp[5, 6])

    a = t_a(-2.5)
    b = t_b(-4.5)
    assert a + b == Fixp[5, 6](-7.0)


def test_signed_sub():
    t_a = Fixp[3, 4]
    t_b = Fixp[4, 5]

    assert (t_a - t_b == Fixp[5, 6])

    a = t_a(-2.5)
    b = t_b(-4.5)
    assert a - b == Fixp[5, 6](2.0)


def test_unsigned_fdiv():
    t_a = Ufixp[4, 6]
    t_b = Ufixp[1, 7]

    assert (t_a // t_b == Ufixp[10, 6])

    assert t_a(15.75) // t_b(0.015625) == Ufixp[10, 6](15.75 / 0.015625)


# def test_signed_fdiv():
#     t_a = Fixp[4, 6]
#     t_b = Fixp[1, 7]

#     assert (t_a // t_b == Fixp[10, 6])

#     assert t_a(-8.0) // t_b(0.9375) == Fixp[10, 6]((-8.0) / 0.9375)


def test_unsigned_div():
    t_a = Ufixp[4, 6]
    t_b = Ufixp[1, 7]

    assert div(t_a(15.75), t_b(0.015625), 0) == Ufixp[10, 6](15.75 / 0.015625)
    assert div(t_a(0.25), t_b(1.984375), 0) == Ufixp[10, 6](0.25 / 1.984375)
    assert div(t_a(0.25), t_b(1.984375), 7) == Ufixp[10, 13](0.25 / 1.984375)

    t_c = Ufixp[10, 6]
    t_d = Ufixp[-2, 12]

    assert div(t_c.max, t_d.lsb, 0) == Ufixp[24, 6](float(t_c.max) / float(t_d.lsb))
    assert div(t_c.max, t_d.max, 0) == Ufixp[24, 6](float(t_c.max) / float(t_d.max))


# def test_signed_div():
#     t_a = Fixp[4, 6]
#     t_b = Fixp[1, 7]

#     assert (t_a / t_b == Fixp[5, 13])

#     assert t_a(-8.0) // t_b(0.9375) == Fixp[5, 13]((-8.0) / 0.9375)


def test_unsigned_mul():
    t_a = Ufixp[4, 6]
    t_b = Ufixp[1, 5]

    assert (t_a * t_b == Ufixp[5, 11])

    assert t_a(15.75) * t_b(1.9375) == Ufixp[5, 11](15.75 * 1.9375)


def test_signed_mul():
    t_a = Fixp[4, 6]
    t_b = Fixp[1, 5]

    assert (t_a * t_b == Fixp[5, 11])

    assert t_a(-8.0) * t_b(0.9375) == Fixp[5, 11]((-8.0) * 0.9375)


def test_signed_unsinged_mix():
    t_a = Ufixp[2, 3]
    t_b = Fixp[3, 4]

    assert (t_a + t_b == Fixp[4, 5])

    a = t_a(3.0)
    b = t_b(-4.0)
    assert a + b == Fixp[4, 5](-1.0)


def test_cast():
    t_a = Ufixp[2, 4]
    t_b = Ufixp[3, 4]

    assert t_b(t_a(2.5)) == t_b(2.5)

    assert t_a(t_b(2.5)) == t_a(2.5)

    # Overflow
    with pytest.raises(ValueError):
        assert t_a(t_b(7.5)) == t_a(3.5)


def test_floor():
    t_a = Fixp[8, 16]

    assert floor(t_a) == Int[8]


def test_add_integer():
    t_a = Ufixp[8, 16]
    t_b = Fixp[8, 16]
    t_c = Uint[16]

    assert t_a + t_c == Ufixp[17, 25]
    assert t_c + t_a == Ufixp[17, 25]

    assert t_a(2) + t_c(2) == Ufixp[17, 25](4)
    assert t_c(2) + t_a(2) == Ufixp[17, 25](4)

    assert t_b + t_c == Fixp[17, 25]
    assert t_c + t_b == Fixp[17, 25]

    assert t_b(-2) + t_c(2) == Fixp[17, 25](0)
    assert t_c(2) + t_b(-2) == Fixp[17, 25](0)


def test_mul_integer():
    t_a = Ufixp[8, 16]
    t_b = Uint[16]

    assert t_a * t_b == Ufixp[24, 32]
    assert t_b * t_a == Ufixp[24, 32]


def test_mul_int():
    a = Ufixp[8, 16](4.0)

    assert type(2 * a) == Fixp[11, 19]
