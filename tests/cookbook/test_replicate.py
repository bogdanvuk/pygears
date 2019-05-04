import pytest

from pygears import Intf
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check

SEQUENCE = [(2, 3), (5, 5), (3, 9), (8, 1)]
REF = list([x[1]] * x[0] for x in SEQUENCE)

T_DIN = Tuple[Uint[16], Uint[16]]


def test_directed(tmpdir, sim_cls):
    directed(drv(t=T_DIN, seq=SEQUENCE), f=replicate(sim_cls=sim_cls), ref=REF)
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(
        drv(t=T_DIN, seq=SEQUENCE) | delay_rng(din_delay, din_delay),
        f=replicate(sim_cls=cosim_cls),
        ref=replicate(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@formal_check()
def test_formal():
    replicate(Intf(T_DIN))


@synth_check({'logic luts': 12, 'ffs': 16})
def test_synth():
    replicate(Intf(T_DIN))
