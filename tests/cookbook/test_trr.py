from nose import with_setup

from pygears import clear
from pygears.cookbook.trr import trr
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from pygears import GearDone, gear
from pygears.typing import TLM
from utils import skip_ifndef


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    directed(
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        f=trr(sim_cls=SimSocket),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_verilate_sim():
    skip_ifndef('VERILATOR_ROOT')
    directed(
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        f=trr(sim_cls=SimVerilated),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_pygears_sim():
    directed(
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        f=trr,
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        drv(t=Queue[Uint[16]], seq=[list(range(9)),
                                    list(range(3))]),
        f=trr(sim_cls=SimSocket),
        ref=trr(name='ref_model'))

    sim()


@gear
async def vir_drv(*, t=Queue[Uint[16]]) -> (TLM['t'], ) * 3:
    x = [list(range(9))]
    for val in x:
        yield (val, None, None)
    for val in x:
        yield (None, val, None)
    for val in x:
        yield (None, None, val)

    raise GearDone


@with_setup(clear)
def test_virdrv_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    sequencers = vir_drv()
    verif(*sequencers, f=trr(sim_cls=SimSocket), ref=trr(name='ref_model'))

    sim()
