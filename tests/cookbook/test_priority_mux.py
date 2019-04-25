from pygears import Intf
from pygears.cookbook import priority_mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Uint, Int, Tuple
from pygears.util.test_utils import formal_check, skip_ifndef


def test_2_inputs(tmpdir, cosim_cls):
    skip_ifndef('RANDOM_TEST')
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


def test_diff_types(tmpdir, cosim_cls):
    skip_ifndef('RANDOM_TEST')
    din0_delay = (1, 1)
    din1_delay = (2, 2)
    din2_delay = (1, 1)
    dout_delay = (0, 0)  # ref model cannot accuratly simulate any other delay

    assert dout_delay[0] == dout_delay[
        1], 'Simulation cannot check random delays for this type of gear'

    seq0 = list(range(5))
    seq1 = [(1, 2), (2, 1), (3, 3), (4, 1), (3, 2)]
    seq2 = list(range(3))

    verif(
        drv(t=Uint[4], seq=seq0)
        | delay_rng(*din0_delay),
        drv(t=Tuple[Uint[8], Uint[3]], seq=seq1)
        | delay_rng(*din1_delay),
        drv(t=Int[3], seq=seq2)
        | delay_rng(*din2_delay),
        f=priority_mux(sim_cls=cosim_cls),
        ref=priority_mux(name='ref_model'),
        delays=[delay_rng(*dout_delay)])

    sim(outdir=tmpdir)


@formal_check(assumes=['s_eventually (din0_valid == 0)'])
def test_uint():
    priority_mux(Intf(Uint[8]), Intf(Uint[8]))
