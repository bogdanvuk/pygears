from nose import with_setup

from pygears import clear, Uint, Queue, Intf, Unit
from pygears.common import quenvelope


@with_setup(clear)
def test_skip():
    iout = quenvelope(Intf(Queue[Uint[1], 3]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]


@with_setup(clear)
def test_all_pass():
    iout = quenvelope(Intf(Queue[Uint[1], 2]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]
