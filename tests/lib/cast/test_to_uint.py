import pytest
from pygears.typing import Uint, Ufixp, Int, Tuple, Fixp, cast


def test_ufixp_type_cast():
    assert cast(Ufixp[8, 16], Uint) == Uint[8]
    assert cast(Ufixp[8, 16], Uint[16]) == Uint[16]
    assert cast(Ufixp[16, 8], Uint) == Uint[16]

    with pytest.raises(TypeError):
        cast(Ufixp[8, 16], Uint[4])

    with pytest.raises(TypeError):
        cast(Ufixp[-1, 16], Uint)


def test_ufixp_value_cast():
    assert cast(Ufixp[8, 16](2.15), Uint) == Uint[8](2)
    assert cast(Ufixp[8, 16](2.15), Uint[16]) == Uint[16](2)

    with pytest.raises(TypeError):
        cast(Ufixp[-1, 16](0.15), Uint)

    assert cast(Ufixp[-1, 16](0.15), Uint[16]) == Uint[16](0)

    with pytest.raises(TypeError):
        cast(Ufixp[8, 16](56.15), Uint[4])


def test_uint_type_cast():
    assert cast(Uint[8], Uint) == Uint[8]
    assert cast(Uint[8], Uint[16]) == Uint[16]

    with pytest.raises(TypeError):
        cast(Uint[16], Uint[8])


def test_uint_value_cast():
    assert cast(Uint[8](128), Uint[16]) == Uint[16](128)

    with pytest.raises(TypeError):
        cast(Uint[16](128), Uint[4])

    assert cast(2.15, Uint[4]) == Uint[4](2)
    assert cast(15, Uint[4]) == Uint[4](15)

    with pytest.raises(ValueError):
        cast(27, Uint[4])


def test_unsupported_cast():
    for t in [Int[6], Tuple[Int[2], Uint[2]], Fixp[1, 14]]:
        with pytest.raises(TypeError):
            cast(t, Uint)
