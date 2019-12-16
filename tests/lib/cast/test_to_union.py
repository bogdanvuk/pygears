from pygears.typing import Tuple, Uint, Union, cast, Unit, Maybe


def test_tuple_type_cast():
    assert cast(Tuple[Uint[4], Uint[1]], Union) == Union[Uint[4], Uint[4]]


def test_maybe_type_cast():
    assert cast(Union[Unit, Uint[4]], Maybe) == Maybe[Uint[4]]
