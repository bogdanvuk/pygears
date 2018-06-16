from nose import with_setup
from pygears import clear
from pygears.sim import sim
from pygears.cookbook.verif import directed
from pygears.sim.modules.seqr import seqr
from pygears.typing import Queue, Uint
from pygears.cookbook.chop import chop


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop,
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

    sim()
