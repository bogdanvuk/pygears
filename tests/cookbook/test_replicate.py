from nose import with_setup

from pygears import clear
from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Tuple, Uint
from utils import skip_ifndef, prepare_result_dir

sequence = [(2, 3), (5, 5), (3, 9), (8, 1)]
ref = list([x[1]] * x[0] for x in sequence)


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence), f=replicate, ref=ref)

    sim()


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimSocket),
        ref=ref)

    sim()


@with_setup(clear)
def test_verilate_sim():
    skip_ifndef('VERILATOR_ROOT')
    directed(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimVerilated),
        ref=ref)

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimSocket),
        ref=replicate(name='ref_model'))

    sim()


@with_setup(clear)
def test_verilate_cosim():
    skip_ifndef('VERILATOR_ROOT')
    verif(
        seqr(t=Tuple[Uint[16], Uint[16]], seq=sequence),
        f=replicate(sim_cls=SimVerilated),
        ref=replicate(name='ref_model'))

    sim()
