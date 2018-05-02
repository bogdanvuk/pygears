from nose import with_setup

from pygears import Intf, clear, bind, find, registry
from pygears.typing import Queue, Tuple, Uint, Int
from pygears.cookbook.rng import rng
from pygears.svgen.generate import svgen_yield
from pygears.svgen import svgen


@with_setup(clear)
def test_basic_unsigned():
    iout = rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert not rng_gear.params['signed']


@with_setup(clear)
def test_basic_signed():
    iout = rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Int[6]]
    assert rng_gear.params['signed']


@with_setup(clear)
def test_supply_constant():
    iout = rng((Uint[4](0), 8, 1))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert rng_gear.params['cfg'] == Tuple[Uint[4], Uint[4], Uint[1]]
    assert not rng_gear.params['signed']


@with_setup(clear)
def test_cnt_only():
    iout = rng(8)

    assert iout.dtype == Queue[Uint[4]]

    rng_gear = find('/rng/rng/sv_rng')
    assert rng_gear.params['cfg'] == Tuple[Uint[1], Uint[4], Uint[1]]


@with_setup(clear)
def test_cnt_down():
    iout = rng((7, 0, -1))

    rng_gear = find('/rng/sv_rng')

    assert rng_gear.params['signed']
    assert rng_gear.params['cfg'] == Tuple[Int[4], Int[2], Int[1]]
    assert iout.dtype == Queue[Int[4]]


@with_setup(clear)
def test_basic_unsigned_svgen():
    rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

    # rng_gear = find('/rng/sv_rng')

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    svtop = svgen()
    for gen, contents in svgen_yield(svtop['rng']):
        print(contents)

    # assert equal_on_nonspace(svtop['ccat'].get_module(TemplateEnv()),
    #                          test_general_ref)

    # assert iout.dtype == Queue[Uint[4]]
    # assert not rng_gear.params['signed']


test_basic_unsigned_svgen()
