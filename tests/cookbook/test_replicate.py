from nose import with_setup

from pygears import clear
from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Tuple, Uint

sequence = [(2, 3), (5, 5), (3, 9), (8, 1)]
ref = list([x[1]] * x[0] for x in sequence)


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence), f=replicate, ref=ref)

    sim()


@with_setup(clear)
def test_socket_sim():
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimSocket),
        ref=ref)

    sim()


@with_setup(clear)
def test_verilate_sim():
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimVerilated),
        ref=ref)

    sim()


@with_setup(clear)
def test_socket_cosim():
    verif(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimSocket),
        ref=replicate(name='ref_model'))

    sim()


@with_setup(clear)
def test_verilate_cosim():
    verif(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimVerilated),
        ref=replicate(name='ref_model'))

    sim()
