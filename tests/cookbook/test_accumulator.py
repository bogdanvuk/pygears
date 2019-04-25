import pytest

from pygears import Intf
from pygears.cookbook import accumulator
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Int, Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check

SEQ_UINT = [[(1, 2), (5, 2), (8, 2)], [(3, 8), (1, 8)],
            [(0, 12), (4, 12), (2, 12), (99, 12)]]
REF_UINT = [16, 12, 117]
T_DIN_UINT = Queue[Tuple[Uint[16], Uint[16]]]

SEQ_INT = [[(1, 2), (5, 2), (-8, 2)], [(-30, 8), (1, 8)]]
REF_INT = [0, -21]
T_DIN_INT = Queue[Tuple[Int[8], Int[8]]]


def test_uint_directed(tmpdir, sim_cls):
    directed(
        drv(t=T_DIN_UINT, seq=SEQ_UINT),
        f=accumulator(sim_cls=sim_cls),
        ref=REF_UINT)
    sim(outdir=tmpdir)


def test_int_directed(tmpdir, sim_cls):
    directed(
        drv(t=T_DIN_INT, seq=SEQ_INT),
        f=accumulator(sim_cls=sim_cls),
        ref=REF_INT)
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_delay(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(
        drv(t=T_DIN_UINT, seq=SEQ_UINT) | delay_rng(din_delay, din_delay),
        f=accumulator(sim_cls=cosim_cls),
        ref=accumulator(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_no_offset(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(
        drv(t=Queue[Uint[8]], seq=[list(
            range(3)), list(range(8))]) | delay_rng(din_delay, din_delay),
        f=accumulator(sim_cls=cosim_cls),
        ref=accumulator(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@formal_check()
def test_formal():
    accumulator(Intf(Queue[Tuple[Uint[8], Uint[8]]]))


@synth_check({'logic luts': 20, 'ffs': 18})
def test_synth():
    accumulator(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
