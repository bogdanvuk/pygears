from nose import with_setup

from pygears import clear, Uint, Queue, Intf, Tuple
from pygears.common import czip


@with_setup(clear)
def test_general():
    iout = czip(
        Intf(Uint[1]), Intf(Queue[Uint[2], 1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Uint[3], Uint[4]], 5]
