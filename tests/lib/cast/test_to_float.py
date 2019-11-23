import pytest
from pygears.typing import Uint, Ufixp, Int, Tuple, Fixp, Float, cast


def test_supported_type_cast():
    for t in [Int[6], Fixp[1, 14], Ufixp[0, 13]]:
        assert cast(t, Float) == Float

    for t in [Tuple[Int[2], Uint[2]]]:
        with pytest.raises(TypeError):
            cast(t, Float)


def test_ufixp_value_cast():
    assert cast(Ufixp[4, 15](2.125), Float) == 2.125
    assert cast(Fixp[4, 15](-2.125), Float) == -2.125


def test_uint_value_cast():
    assert cast(Uint[4](7), Float) == 7.0
    assert cast(Int[4](-7), Float) == -7.0
