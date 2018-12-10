import pytest

from pygears import Intf, MultiAlternativeError, find
from pygears.typing import Queue, Tuple, Uint, Int
from pygears.cookbook.rng import rng

from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv

from pygears.util.test_utils import svgen_check, skip_ifndef


def test_basic_unsigned():
    iout = rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))

    rng_gear = find('/rng/py_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert not rng_gear.params['signed']


def test_basic_unsigned_sim(tmpdir):
    seq = [(2, 8, 2)]
    ref = [list(range(*seq[0]))]

    directed(drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir)


def test_basic_unsigned_cosim(tmpdir, sim_cls):
    seq = [(2, 8, 2)]

    verif(
        drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq),
        f=rng(sim_cls=sim_cls),
        ref=rng(name='ref_model'))

    sim(outdir=tmpdir)


def test_basic_signed():
    iout = rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))

    rng_gear = find('/rng/py_rng')

    assert iout.dtype == Queue[Int[6]]
    assert rng_gear.params['signed']


def test_basic_signed_sim(tmpdir):
    seq = [(-15, -3, 2)]
    ref = [list(range(*seq[0]))]

    directed(drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir)


def test_basic_signed_cosim(tmpdir, sim_cls):
    seq = [(-15, -3, 2)]

    verif(
        drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq),
        f=rng(sim_cls=sim_cls),
        ref=rng(name='ref_model'))

    sim(outdir=tmpdir)


def test_supply_constant():
    iout = rng((Uint[4](0), 8, 1))

    rng_gear = find('/rng/py_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert rng_gear.params['cfg'] == Tuple[{
        'start': Uint[4],
        'cnt': Uint[4],
        'incr': Uint[1]
    }]
    assert not rng_gear.params['signed']


def test_cnt_only():
    iout = rng(8)

    assert iout.dtype == Queue[Uint[4]]

    rng_gear = find('/rng/rng/py_rng')
    assert rng_gear.params['cfg'] == Tuple[Uint[1], Uint[4], Uint[1]]


def test_cnt_only_sim(tmpdir):
    seq = [8]
    ref = [list(range(8))]

    directed(drv(t=Uint[4], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir, check_activity=False)


def test_cnt_only_cosim(tmpdir, sim_cls):
    seq = [8]

    verif(
        drv(t=Uint[4], seq=seq),
        f=rng(sim_cls=sim_cls),
        ref=rng(name='ref_model'))

    sim(outdir=tmpdir, check_activity=False)


def test_cnt_down():
    iout = rng((7, 0, -1))

    rng_gear = find('/rng/py_rng')

    assert rng_gear.params['signed']
    assert rng_gear.params['cfg'] == Tuple[Int[4], Int[2], Int[1]]
    assert iout.dtype == Queue[Int[4]]


@pytest.mark.xfail(raises=MultiAlternativeError)
def test_multi_lvl():
    iout = rng((1, 2, 3), lvl=2)
    print(iout.dtype)


@svgen_check(['rng_hier.sv'])
def test_basic_unsigned_svgen():
    rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))


@svgen_check(['rng_rng.sv', 'rng_ccat.sv', 'rng_hier.sv'])
def test_cnt_svgen():
    rng(8)
