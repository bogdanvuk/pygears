
from pygears.typing_common import cast
from pygears.typing import Tuple, Uint, Queue
from pygears import Intf


def test_type_queue_to_tuple():
    a = Queue[Tuple[Uint[1], Uint[2]], 3]
    assert cast(a, Tuple) == Tuple[Tuple[Uint[1], Uint[2]], Uint[3]]


def test_queue_to_tuple():
    iout = Intf(Queue[Tuple[Uint[1], Uint[2]], 3]) | Tuple
    assert iout.dtype == Tuple[Tuple[Uint[1], Uint[2]], Uint[3]]
