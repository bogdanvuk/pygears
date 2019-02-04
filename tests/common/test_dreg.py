from pygears.cookbook.verif import directed, verif
from pygears.common.dreg import dreg
from pygears.sim import sim, timestep
from pygears.sim.modules.drv import drv
from pygears.typing import Uint


def test_pygears_sim(tmpdir):
    seq = list(range(10))

    directed(drv(t=Uint[16], seq=seq), f=dreg, ref=seq)

    sim(outdir=tmpdir)

    assert timestep() == len(seq)


def test_cosim(tmpdir, cosim_cls):
    seq = list(range(10))
    verif(
        drv(t=Uint[16], seq=seq),
        f=dreg(sim_cls=cosim_cls),
        ref=dreg(name='ref_model'))

    sim(outdir=tmpdir)
