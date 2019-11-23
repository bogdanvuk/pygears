from pygears.typing import Tuple, Uint, Union, cast


def test_tuple_type_cast():
    assert cast(Tuple[Uint[4], Uint[1]], Union) == Union[Uint[4], Uint[4]]
