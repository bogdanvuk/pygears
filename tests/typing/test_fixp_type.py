import pytest
from math import floor, ceil
from pygears.typing import Fixp, Ufixp, typeof, Number, Int, Uint, div, Bool
from pygears.typing import get_match_conds


def test_fixp_is_number():
    get_match_conds(Fixp[1, 2], Number)


def test_wrong_parameter_type():
    with pytest.raises(TypeError):
        Ufixp[2, None]

    with pytest.raises(TypeError):
        Ufixp[2, []]


def test_abs():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    q3_4 = Fixp[3, 4]

    assert abs(uq2_3) == uq2_3
    assert abs(q2_3) == q3_4


def test_add():
    uq2_3 = Ufixp[2, 3]
    uq2_4 = Ufixp[2, 4]
    uq3_4 = Ufixp[3, 4]
    uq3_5 = Ufixp[3, 5]
    uq4_5 = Ufixp[4, 5]
    uq4_6 = Ufixp[4, 6]

    q2_3 = Fixp[2, 3]
    q2_4 = Fixp[2, 4]
    q3_4 = Fixp[3, 4]
    q3_5 = Fixp[3, 5]
    q4_5 = Fixp[4, 5]
    q4_6 = Fixp[4, 6]
    q5_6 = Fixp[5, 6]
    q5_7 = Fixp[5, 7]

    assert uq2_3 + uq3_4 == uq4_5
    assert uq3_4 + uq3_4 == uq4_5

    assert uq2_4 + uq3_4 == uq4_6
    assert uq3_4 + uq3_5 == uq4_6

    assert q2_3 + q3_4 == q4_5
    assert q3_4 + q3_4 == q4_5

    assert q2_4 + q3_4 == q4_6
    assert q3_4 + q3_5 == q4_6

    assert uq2_3 + q3_4 == q4_5
    assert q2_3 + uq3_4 == q5_6
    assert uq3_4 + q3_4 == q5_6
    assert uq2_4 + q3_4 == q4_6
    assert uq3_4 + q3_5 == q5_7
    assert q2_4 + uq3_4 == q5_7


def test_ceil():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    uq4_4 = Ufixp[4, 4]
    q6_3 = Fixp[6, 3]

    assert ceil(uq2_3) == Ufixp[3, 4]
    assert ceil(q2_3) == Fixp[3, 4]
    assert ceil(uq4_4) == uq4_4
    assert ceil(q6_3) == q6_3


def test_float():
    t_a = Ufixp[2, 3]
    t_b = Fixp[3, 4]

    assert (t_a.decode(7) == t_a(3.5))
    assert (t_b.decode(-8) == t_b(-4.0))


def test_floor():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    uq4_4 = Ufixp[4, 4]
    q6_3 = Fixp[6, 3]

    assert floor(uq2_3) == uq2_3
    assert floor(q2_3) == q2_3
    assert floor(uq4_4) == uq4_4
    assert floor(q6_3) == q6_3


def test_ge():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]

    assert (uq2_3 >= q2_3) == Bool
    assert (q2_3 >= uq2_3) == Bool


def test_gt():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]

    assert (uq2_3 > q2_3) == Bool
    assert (q2_3 > uq2_3) == Bool


def test_le():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]

    assert (uq2_3 <= q2_3) == Bool
    assert (q2_3 <= uq2_3) == Bool


def test_lt():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]

    assert (uq2_3 < q2_3) == Bool
    assert (q2_3 < uq2_3) == Bool


def test_lshift():
    uq2_3 = Ufixp[2, 3]
    uq4_3 = Ufixp[4, 3]
    q2_3 = Fixp[2, 3]
    q4_3 = Fixp[4, 3]

    assert uq2_3 << 2 == uq4_3
    assert q2_3 << 2 == q4_3

    assert uq2_3 << 0 == uq2_3
    assert q2_3 << 0 == q2_3


def test_neg():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    q3_4 = Fixp[3, 4]

    assert -uq2_3 == q3_4
    assert -q2_3 == q3_4


def test_round():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    uq4_4 = Ufixp[4, 4]
    q6_3 = Fixp[6, 3]

    assert round(uq2_3) == Ufixp[3, 4]
    assert round(q2_3) == Fixp[3, 4]
    assert round(uq4_4) == uq4_4
    assert round(q6_3) == q6_3


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

    assert div(t_c.max, t_d.quant, 0) == Ufixp[24, 6](float(t_c.max) / float(t_d.quant))
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

    u2 = Uint[2]

    assert t_a(u2(2)) == t_a(2.0)
    assert t_b(u2(2)) == t_b(2.0)

    assert t_a(3) == t_a(3.0)


def test_signed_cast():
    t_a = Fixp[2, 4]
    t_b = Fixp[3, 4]

    assert t_b(t_a(-1.5)) == t_b(-1.5)

    assert t_a(t_b(-1.5)) == t_a(-1.5)

    # Overflow
    with pytest.raises(ValueError):
        assert t_a(t_b(3.5)) == t_a(3.5)

    u2 = Uint[2]
    i3 = Int[3]

    assert t_a(u2(1)) == t_a(1.0)
    assert t_b(u2(1)) == t_b(1.0)

    assert t_a(i3(-2)) == t_a(-2)
    assert t_b(i3(-2)) == t_b(-2)


# def test_floor():
#     t_a = Fixp[8, 16]

#     assert floor(t_a) == Int[8]


def test_add_integer():
    t_a = Ufixp[8, 16]
    t_b = Fixp[8, 16]
    t_c = Uint[16]

    assert t_a + t_c == Ufixp[17, 25]
    assert t_c + t_a == Ufixp[17, 25]

    assert t_a(2) + t_c(2) == Ufixp[17, 25](4)
    assert t_c(2) + t_a(2) == Ufixp[17, 25](4)

    assert t_b + t_c == Fixp[18, 26]
    assert t_c + t_b == Fixp[18, 26]

    assert t_b(-2) + t_c(2) == Fixp[18, 26](0)
    assert t_c(2) + t_b(-2) == Fixp[18, 26](0)


def test_mul_integer():
    t_a = Ufixp[8, 16]
    t_b = Uint[16]

    assert t_a * t_b == Ufixp[24, 32]
    assert t_b * t_a == Ufixp[24, 32]


def test_mul_int():
    a = Ufixp[8, 16](4.0)

    assert type(2 * a) == Fixp[11, 19]
