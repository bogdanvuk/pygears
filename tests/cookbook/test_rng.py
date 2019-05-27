import pytest

from pygears import Intf, find
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.rng import py_rng, rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Int, Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


def test_basic_unsigned():
    iout = rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))
    assert iout.dtype == Queue[Uint[4]]


def test_basic_unsigned_sim(tmpdir):
    seq = [(2, 8, 2)]
    ref = [list(range(*seq[0]))]

    directed(drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('cnt_steps', [True, False])
@pytest.mark.parametrize('incr_steps', [True, False])
def test_unsigned_cosim(tmpdir, cosim_cls, din_delay, dout_delay, cnt_steps,
                        incr_steps):
    seq = [(2, 8, 2)]

    verif(
        drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq)
        | delay_rng(din_delay, din_delay),
        f=rng(sim_cls=cosim_cls, cnt_steps=cnt_steps, incr_steps=incr_steps),
        ref=rng(name='ref_model', cnt_steps=cnt_steps, incr_steps=incr_steps),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_basic_signed():
    iout = rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))
    assert iout.dtype == Queue[Int[6]]


def test_basic_signed_sim(tmpdir):
    seq = [(-15, -3, 2)]
    ref = [list(range(*seq[0]))]

    directed(drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir)


# tmpdir = local('/tmp/pytest-of-bogdan/pytest-1/popen-gw0/test_signed_cosim_cosim_cls0_00')
# cosim_cls = functools.partial(<class 'pygears.sim.modules.verilator.SimVerilated'>, language='v')
# din_delay = 0, dout_delay = 0

@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_signed_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    seq = [(-15, -3, 2)]

    verif(
        drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq)
        | delay_rng(din_delay, din_delay),
        f=rng(sim_cls=cosim_cls),
        ref=rng(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

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


def test_cnt_only():
    iout = rng(8)

    assert iout.dtype == Queue[Uint[4]]

    rng_gear = find('/rng/rng/py_rng')
    assert rng_gear.params['cfg'] == Tuple[Uint[1], Uint[4], Uint[1]]


def test_cnt_only_sim(tmpdir):
    seq = [8]
    ref = [list(range(8))]

    directed(drv(t=Uint[4], seq=seq), f=rng, ref=ref)

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cnt_only_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    seq = [8]

    verif(
        drv(t=Uint[4], seq=seq)
        | delay_rng(din_delay, din_delay),
        f=rng(sim_cls=cosim_cls),
        ref=rng(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_cnt_down():
    iout = rng((7, 0, -1))

    rng_gear = find('/rng/py_rng')

    assert rng_gear.params['cfg'] == Tuple[Int[4], Int[2], Int[1]]
    assert iout.dtype == Queue[Int[4]]


# @pytest.mark.xfail(raises=MultiAlternativeError)
# def test_multi_lvl():
#     iout = rng((1, 2, 3), lvl=2)
#     print(iout.dtype)

# @svgen_check(['rng_hier.sv'])
# def test_basic_unsigned_svgen():
#     rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

# @svgen_check(['rng_rng.sv', 'rng_ccat.sv', 'rng_hier.sv'])
# def test_cnt_svgen():
#     rng(8)

# TODO : hierarchy must be avoided for verilog (so py_rng, not rng)


@formal_check()
def test_basic_formal():
    py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))


@formal_check()
def test_cnt_steps_formal():
    py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]), cnt_steps=True)


@formal_check()
def test_incr_cnt_steps_formal():
    py_rng(
        Intf(Tuple[Uint[4], Uint[4], Uint[2]]),
        cnt_steps=True,
        incr_steps=True)
