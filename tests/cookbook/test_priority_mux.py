from pygears import Intf
from pygears.cookbook import priority_mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Int, Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, skip_ifndef


def test_2_inputs(tmpdir, cosim_cls):
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


def test_diff_types(tmpdir, sim_cls):
    din0_delay = (1, 1)
    din1_delay = (2, 2)
    din2_delay = (1, 1)

    seq0 = list(range(5))
    seq1 = [(1, 2), (2, 1), (3, 3), (4, 1), (3, 2)]
    seq2 = list(range(3))

    directed(
        drv(t=Uint[4], seq=seq0)
        | delay_rng(*din0_delay),
        drv(t=Tuple[Uint[8], Uint[3]], seq=seq1)
        | delay_rng(*din1_delay),
        drv(t=Int[3], seq=seq2)
        | delay_rng(*din2_delay),
        f=priority_mux(sim_cls=sim_cls),
        ref=[(0, 0), (513, 1), (1, 0), (0, 2), (2, 0), (258, 1), (3, 0), (1,
                                                                          2),
             (4, 0), (771, 1), (2, 2), (260, 1), (515, 1)])

    sim(outdir=tmpdir)


def test_queue(tmpdir, sim_cls):
    din0_delay = (1, 1)
    din1_delay = (2, 2)
    din2_delay = (1, 1)

    seq0 = [list(range(3)), list(range(2)), list(range(4, 8))]
    seq1 = [list(range(7, 8)), list(range(6, 9))]
    seq2 = [list(range(0, 2)), list(range(9, 11))]

    directed(
        drv(t=Queue[Uint[4]], seq=seq0)
        | delay_rng(*din0_delay),
        drv(t=Queue[Uint[4]], seq=seq1)
        | delay_rng(*din1_delay),
        drv(t=Queue[Uint[4]], seq=seq2)
        | delay_rng(*din2_delay),
        f=priority_mux(sim_cls=sim_cls),
        ref=[[(0, 0), (1, 0), (2, 0)], [(7, 1)], [(0, 0), (1, 0)],
             [(6, 1), (7, 1), (8, 1)], [(4, 0), (5, 0), (6, 0), (7, 0)],
             [(0, 2), (1, 2)], [(9, 2), (10, 2)]])

    sim(outdir=tmpdir)


@formal_check(assumes=['s_eventually (din0_valid == 0)'])
def test_uint():
    priority_mux(Intf(Uint[8]), Intf(Uint[8]))
