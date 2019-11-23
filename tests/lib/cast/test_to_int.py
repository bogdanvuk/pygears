import pytest
from pygears.typing import Int, Tuple, Ufixp, Uint, cast


def test_ufixp_type_cast():
    assert cast(Ufixp[8, 16], Int) == Int[9]
    assert cast(Ufixp[8, 16], Int[16]) == Int[16]
    assert cast(Ufixp[16, 8], Int) == Int[17]

    with pytest.raises(TypeError):
        cast(Ufixp[-1, 16], Int)


def test_ufixp_value_cast():
    assert cast(Ufixp[8, 16](2.15), Int) == Int[9](2)
    assert cast(Ufixp[8, 16](2.15), Int[16]) == Int[16](2)

    with pytest.raises(TypeError):
        cast(Ufixp[-1, 16](0.15), Int)

    assert cast(Ufixp[-1, 16](0.15), Int[16]) == Int[16](0)

    with pytest.raises(TypeError):
        cast(Ufixp[8, 16](56.15), Int[8])


def test_uint_type_cast():
    assert cast(Uint[8], Int) == Int[9]
    assert cast(Uint[8], Int[16]) == Int[16]

    with pytest.raises(TypeError):
        cast(Uint[8], Int[8])

    assert cast(Int[8], Int) == Int[8]
    assert cast(Int[8], Int[16]) == Int[16]

    with pytest.raises(TypeError):
        cast(Int[8], Int[4])


def test_number_value_cast():
    assert cast(Uint[8](128), Int[16]) == Int[16](128)

    assert cast(Int[8](127), Int[8]) == Int[8](127)

    with pytest.raises(TypeError):
        cast(Uint[16](128), Int[16])

    with pytest.raises(TypeError):
        cast(Int[16](-128), Int[8])

    assert cast(2.15, Int[4]) == Int[4](2)
    assert cast(7, Int[4]) == Int[4](7)
    assert cast(-8, Int[4]) == Int[4](-8)

    with pytest.raises(ValueError):
        cast(-9, Int[4])


def test_unsupported_cast():
    for t in [Tuple[Int[2], Uint[2]]]:
        with pytest.raises(TypeError):
            cast(t, Int)
