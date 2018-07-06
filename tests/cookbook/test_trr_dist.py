from nose import with_setup

from pygears import clear
from pygears.cookbook.trr_dist import trr_dist
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.typing import Queue, Uint
from utils import skip_ifndef

seq = [[list(range(9)), list(range(3))], [list(range(4)), list(range(7))]]
ref0 = [seq[0][0], seq[1][0]]
ref1 = [seq[0][1], seq[1][1]]


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(dout_num=2),
        ref=[ref0, ref1])

    sim()


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    directed(
        seqr(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=SimSocket, dout_num=2),
        ref=[ref0, ref1])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    num = 2
    verif(
        seqr(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=SimSocket, dout_num=num),
        ref=trr_dist(name='ref_model', dout_num=num))

    sim()
