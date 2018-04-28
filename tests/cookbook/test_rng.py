from nose import with_setup

from pygears import Intf, clear, bind, find
from pygears.common import czip
from pygears.typing import Queue, Tuple, Uint, Int
from pygears.cookbook.rng import rng


@with_setup(clear)
def test_basic_unsigned():
    iout = rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

    rng_gear = find('/rng')

    assert iout.dtype == Queue[Uint[4]]
    assert not rng_gear.params['signed']


@with_setup(clear)
def test_basic_signed():
    iout = rng(Intf(Tuple[Int[4], Uint[2], Uint[2]]))

    rng_gear = find('/rng')

    assert iout.dtype == Queue[Int[4]]
    assert rng_gear.params['signed']


@with_setup(clear)
def test_supply_constant():
    iout = rng((Uint[4](0), 1, 8))

    rng_gear = find('/rng')

    assert iout.dtype == Queue[Uint[1]]
    assert not rng_gear.params['signed']


bind('ErrReportLevel', 0)
test_supply_constant()
