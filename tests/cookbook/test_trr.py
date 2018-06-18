from nose import with_setup

from pygears import clear
from pygears.cookbook.trr import trr
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.typing import Queue, Uint


@with_setup(clear)
def test_socket_sim():
    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        f=trr(sim_cls=SimSocket),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim(outdir='/tools/home/tmp')


test_socket_sim()
