from nose import with_setup

from pygears import clear
from pygears.cookbook.trr import trr
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.seqr import seqr
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from pygears import GearDone, gear
from pygears.typing import TLM


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

    sim()


@with_setup(clear)
def test_verilate_sim():
    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        f=trr(sim_cls=SimVerilated),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_pygears_sim():
    directed(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        f=trr,
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_socket_cosim():
    verif(
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        seqr(t=Queue[Uint[16]], seq=[list(range(9)),
                                     list(range(3))]),
        f=trr(sim_cls=SimSocket),
        ref=trr(name='ref_model'))

    sim()


@gear
async def vir_seqr(*, t=Queue[Uint[16]]) -> (TLM['t'], ) * 3:
    x = [list(range(9))]
    for val in x:
        yield (val, None, None)
    for val in x:
        yield (None, val, None)
    for val in x:
        yield (None, None, val)

    raise GearDone


@with_setup(clear)
def test_virseqr_cosim():
    sequencers = vir_seqr()
    verif(*sequencers, f=trr(sim_cls=SimSocket), ref=trr(name='ref_model'))

    sim(outdir='/tools/home/tmp1')


test_virseqr_cosim()
