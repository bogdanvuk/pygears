import pytest

from pygears.common.dreg import dreg
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim, timestep
from pygears.sim.modules.drv import drv
from pygears.typing import Uint


def test_pygears_sim(tmpdir):
    seq = list(range(10))

    directed(drv(t=Uint[16], seq=seq), f=dreg, ref=seq)

    sim(outdir=tmpdir)

    assert timestep() == len(seq)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    seq = list(range(10))
    verif(
        drv(t=Uint[16], seq=seq) | delay_rng(din_delay, din_delay),
        f=dreg(sim_cls=cosim_cls),
        ref=dreg(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)
