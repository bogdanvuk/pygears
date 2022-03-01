from pygears.lib import sot_queue, directed, drv
from pygears.typing import Queue, Uint
from pygears.sim import sim


def test_lvl1(cosim_cls):
    directed(drv(t=Queue[Uint[4]], seq=[list(range(4)),
                                        list(range(4))]),
             f=sot_queue(sim_cls=cosim_cls),
             ref=[(0, 1), (1, 0), (2, 0), (3, 0), (0, 1), (1, 0), (2, 0),
                  (3, 0)])

    sim()

def test_lvl2(cosim_cls):
    directed(drv(t=Queue[Uint[4], 2], seq=[[[0, 1], [2, 3]]]),
             f=sot_queue(sim_cls=cosim_cls),
             ref=[(0, 3), (1, 2), (2, 1), (3, 0)])

    sim()


def test_lvl3(cosim_cls):
    from pygears.lib import sot_queue, directed
    directed(drv(t=Queue[Uint[4], 3], seq=[[[[0, 1], [2, 3]], [[4, 5], [6, 7]]]]),
             f=sot_queue(sim_cls=cosim_cls),
             ref=[(0, 7), (1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1), (7, 0)])

    sim()
