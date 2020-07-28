from math import ceil, floor
from pygears.typing import Fixp, Ufixp, Uint, Int


def test_abs():
    uq2_3 = Ufixp[2, 3]
    q2_3 = Fixp[2, 3]
    q3_4 = Fixp[3, 4]

    assert abs(uq2_3.max) == uq2_3.max
    assert abs(q2_3.min) == q3_4(abs(float(q2_3.min)))


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

    assert uq2_3.quant + uq3_4.quant == uq4_5(float(uq2_3.quant) + float(uq3_4.quant))
    assert uq2_3.max + uq3_4.max == uq4_5(11.0)
    assert uq3_4.max + uq3_4.max == uq4_5(15.0)

    assert uq2_4.quant + uq3_4.quant == uq4_6(float(uq2_4.quant) + float(uq3_4.quant))
    assert uq2_4.max + uq3_4.max == uq4_6(11.25)
    assert uq3_4.max + uq3_5.max == uq4_6(15.25)

    assert q2_3.quant + q3_4.quant == q4_5(float(q2_3.quant) + float(q3_4.quant))
    assert q2_3.max + q3_4.max == q4_5(5.0)
    assert q3_4.max + q3_4.max == q4_5(7.0)

    assert q2_4.quant + q3_4.quant == q4_6(float(q2_4.quant) + float(q3_4.quant))
    assert q2_4.max + q3_4.max == q4_6(5.25)
    assert q3_4.max + q3_5.max == q4_6(7.25)

    assert uq2_3.quant + q3_4.quant == q4_5(float(uq2_3.quant) + float(q3_4.quant))
    assert uq2_3.max + q3_4.max == q4_5(7.0)
    assert q2_3.max + uq3_4.max == q5_6(9.0)

    assert uq3_4.max + q3_4.max == q5_6(11.0)

    assert uq2_4.quant + q3_4.quant == q4_6(float(uq2_4.quant) + float(q3_4.quant))
    assert uq2_4.max + q3_4.max == q4_6(7.25)
    assert uq3_4.max + q3_5.max == q5_7(11.25)
    assert q2_4.max + uq3_4.max == q5_7(9.25)

    assert q2_3.min + q3_4.max == q4_5(1.5)
    assert q3_4.min + q3_4.max == q4_5(-0.5)

    assert q2_4.min + q3_4.max == q4_6(1.5)
    assert q3_4.min + q3_5.max == q4_6(-0.25)

    assert uq2_3.max + q3_4.min == q4_5(-0.5)
    assert q2_3.min + uq3_4.max == q5_6(5.5)

    assert uq3_4.max + q3_4.min == q5_6(3.5)

    assert uq2_4.max + q3_4.min == q4_6(-0.25)
    assert uq3_4.max + q3_5.min == q5_7(3.5)
    assert q2_4.min + uq3_4.max == q5_7(5.5)


def test_ceil():
    uq2_4 = Ufixp[2, 4]
    q2_3 = Fixp[2, 3]
    uq4_4 = Ufixp[4, 4]
    q6_3 = Fixp[6, 3]

    assert ceil(uq2_4.max) == Ufixp[3, 5](4.0)
    assert ceil(uq2_4(3.25)) == Ufixp[3, 5](4.0)
    assert ceil(q2_3.min) == Fixp[3, 4](-2.0)
    assert ceil(q2_3(-1.5)) == Fixp[3, 4](-1.0)
    assert ceil(uq4_4.max) == uq4_4.max
    assert ceil(q6_3.min) == q6_3.min


def test_floor():
    uq2_4 = Ufixp[2, 4]
    q2_3 = Fixp[2, 3]
    uq4_4 = Ufixp[4, 4]
    q6_3 = Fixp[6, 3]

    assert floor(uq2_4.max) == uq2_4(3.0)
    assert floor(uq2_4(3.25)) == uq2_4(3.0)
    assert floor(q2_3.min) == q2_3(-2.0)
    assert floor(q2_3(-1.5)) == q2_3(-2.0)
    assert floor(uq4_4.max) == uq4_4.max
    assert floor(q6_3.min) == q6_3.min


def test_lshift():
    uq2_3 = Ufixp[2, 3]
    uq4_3 = Ufixp[4, 3]
    q2_3 = Fixp[2, 3]
    q4_3 = Fixp[4, 3]

    assert uq2_3.max << 2 == uq4_3(14.0)
    assert q2_3.min << 2 == q4_3.min

    assert uq2_3.max << 0 == uq2_3.max
    assert q2_3.min << 0 == q2_3.min


def test_sub_val():
    uq2_3 = Ufixp[2, 3]
    uq2_4 = Ufixp[2, 4]
    uq3_4 = Ufixp[3, 4]
    uq3_5 = Ufixp[3, 5]

    q2_3 = Fixp[2, 3]
    q2_4 = Fixp[2, 4]
    q3_4 = Fixp[3, 4]
    q3_5 = Fixp[3, 5]
    q4_5 = Fixp[4, 5]
    q4_6 = Fixp[4, 6]
    q5_6 = Fixp[5, 6]
    q5_7 = Fixp[5, 7]

    assert uq2_3.quant - uq3_4.quant == q4_5(0.0)
    assert uq2_3.min - uq3_4.max == q4_5(-7.5)

    assert uq2_4.quant - uq3_4.quant == q4_6(float(uq2_4.quant) - float(uq3_4.quant))

    assert uq2_4.min - uq3_4.max == q4_6(-7.5)
    assert uq3_4.min - uq3_5.max == q4_6(-7.75)

    assert q2_3.quant - q3_4.quant == q4_5(0.0)
    assert q2_3.min - q3_4.max == q4_5(-5.5)
    assert q3_4.min - q3_4.max == q4_5(-7.5)
    assert q3_4.max - q3_4.min == q4_5(7.5)

    assert q2_4.quant - q3_4.quant == q4_6(float(q2_4.quant) - float(q3_4.quant))
    assert q2_4.min - q3_4.max == q4_6(-5.5)
    assert q2_4.max - q3_4.min == q4_6(5.75)

    assert q3_4.min - q3_5.max == q4_6(-7.75)
    assert q3_4.max - q3_5.min == q4_6(7.5)

    assert uq2_3.quant - q3_4.quant == q4_5(0.0)
    assert uq2_3.max - q3_4.min == q4_5(7.5)
    assert q2_3.min - uq3_4.max == q5_6(-9.5)

    assert uq3_4.max - q3_4.min == q5_6(11.5)
    assert q3_4.min - uq3_4.max == q5_6(-11.5)

    assert uq2_4.quant - q3_4.quant == q4_6(float(uq2_4.quant) - float(q3_4.quant))
    assert uq2_4.max - q3_4.min == q4_6(7.75)
    assert uq3_4.max - q3_5.min == q5_7(11.5)
    assert q2_4.min - uq3_4.max == q5_7(-9.5)
