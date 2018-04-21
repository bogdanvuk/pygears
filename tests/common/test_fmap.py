from nose import with_setup
from nose.tools import raises

from pygears import Intf, Queue, Uint, clear, gear
from pygears.common import fmap
from pygears.core.gear import GearMatchError


@raises(GearMatchError)
@with_setup(clear)
def test_simple_fail():
    @gear
    def test(din: Uint[4]) -> Uint[2]:
        pass

    fmap(Intf(Queue[Uint[4], 2]), f=test)


@with_setup(clear)
def test_simple():
    @gear
    def test(din: Uint[4]) -> Uint[2]:
        pass

    iout = fmap(Intf(Queue[Uint[4], 2]), f=test, lvl=2)
    assert iout.dtype == Queue[Uint[2], 2]
