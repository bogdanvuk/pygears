from pygears.lib import sot_queue, directed, drv
from pygears.typing import Queue, Uint
from pygears.sim import sim


def test_lvl1(tmpdir, cosim_cls):
    directed(drv(t=Queue[Uint[4]], seq=[list(range(4)),
                                        list(range(4))]),
             f=sot_queue(sim_cls=cosim_cls),
             ref=[(0, 1), (1, 0), (2, 0), (3, 0), (0, 1), (1, 0), (2, 0),
                  (3, 0)])

    sim(tmpdir)


def test_lvl2(tmpdir, cosim_cls):
    directed(drv(t=Queue[Uint[4], 2], seq=[[[0, 1], [2, 3]]]),
             f=sot_queue(sim_cls=cosim_cls),
             ref=[(0, 3), (1, 2), (2, 1), (3, 0)])

    sim(tmpdir)


# from pygears.sim.modules import SimVerilated
# test_lvl2('/tools/home/tmp/sot_queuee', SimVerilated)
