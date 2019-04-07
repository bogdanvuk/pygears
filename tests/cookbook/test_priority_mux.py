from pygears.cookbook import priority_mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Uint
from pygears.util.test_utils import skip_ifndef


def test_directed(tmpdir, cosim_cls):
    # skip_ifndef('RANDOM_TEST')
    # din0_delay = (0, 5)
    # din1_delay = (0, 5)
    din0_delay = (1, 1)
    din1_delay = (2, 2)
    dout_delay = (3, 3)

    assert dout_delay[0] == dout_delay[
        1], 'Simulation cannot check random delays for this type of gear'

    seq0 = list(range(10))
    seq1 = list(range(10, 20))

    verif(
        drv(t=Uint[8], seq=seq0)
        | delay_rng(*din0_delay),
        drv(t=Uint[8], seq=seq1)
        | delay_rng(*din1_delay),
        f=priority_mux(sim_cls=cosim_cls),
        ref=priority_mux(name='ref_model'),
        delays=[delay_rng(*dout_delay)])

    sim(outdir=tmpdir)
