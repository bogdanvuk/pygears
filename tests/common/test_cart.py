from nose import with_setup

from pygears import clear, Uint, Queue, Intf, Tuple, Unit
from pygears.common import cart


@with_setup(clear)
def test_two():
    iout = cart(Intf(Queue[Unit, 3]), Intf(Uint[1]))

    assert iout.dtype == Queue[Tuple[Unit, Uint[1]], 3]


@with_setup(clear)
def test_multiple():
    iout = cart(
        Intf(Uint[1]), Intf(Queue[Uint[2], 1]), Intf(Queue[Unit, 3]),
        Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Unit, Uint[4]], 9]

from pygears import bind
bind('ErrReportLevel', 0)
test_two()
