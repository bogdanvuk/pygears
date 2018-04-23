from nose import with_setup
from nose.tools import raises

from pygears import Intf, Queue, Uint, clear, gear, Tuple, bind
from pygears.common import fmap
from pygears.core.gear import GearMatchError


@raises(GearMatchError)
@with_setup(clear)
def test_queuemap_simple_fail():
    @gear
    def test(din: Uint[4]) -> Uint[2]:
        pass

    fmap(Intf(Queue[Uint[4], 2]), f=test)


@with_setup(clear)
def test_queuemap_simple():
    @gear
    def test(din: Uint[4]) -> Uint[2]:
        pass

    iout = fmap(Intf(Queue[Uint[4], 2]), f=test, lvl=2)
    assert iout.dtype == Queue[Uint[2], 2]


@raises(GearMatchError)
@with_setup(clear)
def test_tuplemap_simple_fail():
    @gear
    def test(din: Uint['size']) -> Uint['size+1']:
        pass

    fmap(Intf(Tuple[Uint[1], Uint[2]]), f=test)


@with_setup(clear)
def test_tuplemap_simple():
    @gear
    def test(din: Uint['size']) -> Uint['size+1']:
        pass

    iout = fmap(Intf(Tuple[Uint[1], Uint[2]]), f=(test, test))
    assert iout.dtype == Tuple[Uint[2], Uint[3]]


@with_setup(clear)
def test_queuemap_tuplemap():
    @gear
    def test(din: Uint['size']) -> Uint['size+1']:
        pass

    iout = fmap(Intf(Queue[Tuple[Uint[1], Uint[2]], 2]), f=(test, test), lvl=3)
    assert iout.dtype == Queue[Tuple[Uint[2], Uint[3]], 2]
