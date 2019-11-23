import pytest
from pygears.typing import Tuple, Uint, Queue, cast


def test_tuple_type_cast():
    assert cast(Tuple[Uint[4], Uint[2]], Queue) == Queue[Uint[4], 2]

    with pytest.raises(TypeError):
        cast(Tuple[Uint[4], Uint[2]], Queue[Uint[2]])

    with pytest.raises(TypeError):
        cast(Tuple[Uint[4], Uint[2]], Queue[Uint[2], 2])
