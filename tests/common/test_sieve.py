from nose import with_setup

from pygears import Intf, clear
from pygears.typing import Tuple, Uint
from pygears.common import sieve


@with_setup(clear)
def test_explicit_tuple_single():
    iout = sieve(Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]]), index=0)

    assert iout.dtype == Uint[1]


@with_setup(clear)
def test_explicit_tuple_slice():
    iout = sieve(
        Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]]), index=slice(1, 3))

    assert iout.dtype == Tuple[Uint[2], Uint[3]]


@with_setup(clear)
def test_explicit_tuple_multi_slice():
    iout = sieve(
        Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]]),
        index=(slice(0, 2), 3))

    assert iout.dtype == Tuple[Uint[1], Uint[2], Uint[4]]


@with_setup(clear)
def test_indexing_tuple_single():
    iout = Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]])[0]

    assert iout.dtype == Uint[1]


@with_setup(clear)
def test_indexing_tuple_slice():
    iout = Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]])[1:3]

    assert iout.dtype == Tuple[Uint[2], Uint[3]]


@with_setup(clear)
def test_indexing_tuple_multi_slice():
    iout = Intf(Tuple[Uint[1], Uint[2], Uint[3], Uint[4]])[:2, 3]

    assert iout.dtype == Tuple[Uint[1], Uint[2], Uint[4]]
