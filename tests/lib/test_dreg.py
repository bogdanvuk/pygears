import pytest

from pygears import Intf, gear
from pygears.lib import decoupler, dreg
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim, timestep
from pygears.typing import Int, Queue, Tuple, Uint, Unit
from pygears.util.test_utils import formal_check, synth_check


def test_pygears_sim(tmpdir):
    seq = list(range(10))

    directed(drv(t=Uint[16], seq=seq), f=dreg, ref=seq)

    sim(outdir=tmpdir)

    assert timestep() == len(seq)


def get_dut(dout_delay):
    @gear
    def decoupled(din):
        return din | dreg | decoupler

    if dout_delay == 0:
        return decoupled
    return dreg


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    seq = list(range(1, 10))
    dut = get_dut(dout_delay)
    directed(drv(t=Uint[16], seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=cosim_cls),
             ref=seq,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_queue_tuple(tmpdir, cosim_cls, din_delay, dout_delay):
    seq = [[(0, 1), (4, 0), (1, 1)], [(1, 1), (2, 0), (3, 1), (4, 0)]]
    dut = get_dut(dout_delay)
    verif(drv(t=Queue[Tuple[Uint[16], Int[2]]], seq=seq)
          | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=dreg(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('lvl', [1, 2, 5])
def test_queue_unit(tmpdir, cosim_cls, lvl):
    # sequence represents eot values
    # cast to Queue[Unit] after driver
    seq = [0, 0, 1, 2, 1, 2, 3]

    verif(drv(t=Uint[8], seq=seq) | Queue[Unit, lvl],
          f=dreg(sim_cls=cosim_cls),
          ref=dreg(name='ref_model'))

    sim(outdir=tmpdir)


@formal_check()
def test_formal():
    dreg(Intf(Uint[16]))


@synth_check({'logic luts': 2, 'ffs': 17}, tool='vivado')
def test_synth_vivado():
    dreg(Intf(Uint[16]))


@synth_check({'logic luts': 20, 'ffs': 17}, tool='yosys')
def test_synth_yosys():
    dreg(Intf(Uint[16]))
