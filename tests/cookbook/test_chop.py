from nose import with_setup

from pygears import clear, registry
from pygears.cookbook.chop import chop
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import skip_ifndef


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop,
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

    sim()


@with_setup(clear)
def test_verilator_sim():
    skip_ifndef('VERILATOR_ROOT')

    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop(sim_cls=SimVerilated),
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

    sim()


@with_setup(clear)
def test_verilator_cosim():
    skip_ifndef('VERILATOR_ROOT')

    verif(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop(sim_cls=SimVerilated),
        ref=chop(name='ref_model'))

    sim()


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')

    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop(sim_cls=SimSocket),
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')

    registry('SimConfig')['dbg_assert'] = True
    verif(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Uint[16], seq=[2, 3]),
        f=chop(sim_cls=SimSocket),
        ref=chop(name='ref_model'))

    sim()
