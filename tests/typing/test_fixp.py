from pygears.typing import Fixp, Ufixp, Unit, Bool


def test_float():
    t_a = Ufixp[2, 3]
    t_b = Fixp[3, 4]

    assert (t_a(7) == t_a(3.5))
    assert (t_b(-9) == t_b(-4.5))


def test_unsigned_add():
    t_a = Ufixp[2, 3]
    t_b = Ufixp[3, 4]

    assert (t_a + t_b == Ufixp[4, 5])

    a = t_a(3.5)
    b = t_b(7.5)
    assert a + b == Ufixp[4, 5](11.0)


def test_signed_add():
    t_a = Fixp[2, 3]
    t_b = Fixp[3, 4]

    assert (t_a + t_b == Fixp[4, 5])

    a = t_a(-2.5)
    b = t_b(-4.5)
    assert a + b == Fixp[4, 5](-7.0)


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
    assert t_a(t_b(7.5)) == t_a(3.5)
