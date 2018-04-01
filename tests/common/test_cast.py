from pygears.common.cast import typing
from pygears import Tuple, Uint, Queue


def test_queue_to_tuple():
    a = Queue[Tuple[Uint[1], Uint[2]], 3]
    assert typing.cast(a, Tuple) == Tuple[Tuple[Uint[1], Uint[2]], Uint[3]]
