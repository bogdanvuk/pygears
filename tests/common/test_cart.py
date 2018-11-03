
from pygears import Intf
from pygears.typing import Uint, Queue, Tuple, Unit
from pygears.common import cart


def test_two():
    iout = cart(Intf(Queue[Unit, 3]), Intf(Uint[1]))

    assert iout.dtype == Queue[Tuple[Unit, Uint[1]], 3]


def test_multiple():
    iout = cart(
        Intf(Uint[1]), Intf(Queue[Uint[2], 1]), Intf(Queue[Unit, 3]),
        Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Unit, Uint[4]], 9]
