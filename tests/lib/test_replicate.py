import pytest

from pygears import Intf, gear
from pygears.lib import decoupler
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check

SEQUENCE = [(2, 3), (5, 5), (3, 9), (8, 1)]
REF = list([x[1]] * x[0] for x in SEQUENCE)

T_DIN = Tuple[Uint[16], Uint[16]]


def get_dut(dout_delay):
    @gear
    def decoupled(din):
        return din | replicate | decoupler

    if dout_delay == 0:
        return decoupled
    return replicate


def test_directed(tmpdir, sim_cls):
    directed(drv(t=T_DIN, seq=SEQUENCE), f=replicate(sim_cls=sim_cls), ref=REF)
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    dut = get_dut(dout_delay)
    verif(
        drv(t=T_DIN, seq=SEQUENCE) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=cosim_cls),
        ref=replicate(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


# TODO: live fails
# @formal_check()
# def test_formal():
#     replicate(Intf(T_DIN))


@synth_check({'logic luts': 12, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    replicate(Intf(T_DIN))


@synth_check({'logic luts': 117, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    replicate(Intf(T_DIN))
