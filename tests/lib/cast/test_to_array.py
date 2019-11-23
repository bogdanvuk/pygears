import pytest
from pygears.typing import Array, Tuple, Uint, cast


def test_tuple_type_cast():
    assert cast(Tuple[Uint[4], Uint[4], Uint[4]], Array) == Array[Uint[4], 3]

    with pytest.raises(TypeError):
        cast(Tuple[Uint[4], Uint[5], Uint[6]], Array)

    assert cast(Tuple[Uint[6], Uint[4], Uint[4]], Array) == Array[Uint[6], 3]

    assert cast(Tuple[Uint[4], Uint[4], Uint[4]],
                Array[Uint[6]]) == Array[Uint[6], 3]

    with pytest.raises(TypeError):
        cast(Tuple[Uint[4], Uint[4], Uint[4]], Array[Uint[2]])

    assert cast(Tuple[Uint[4], Uint[4], Uint[4]],
                Array[Uint[6], 3]) == Array[Uint[6], 3]

    with pytest.raises(TypeError):
        cast(Tuple[Uint[4], Uint[4], Uint[4]], Array[Uint[4], 2])
