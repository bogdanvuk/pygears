from functools import partial


from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import prepare_result_dir, skip_ifndef

sequence = [(2, 3), (5, 5), (3, 9), (8, 1)]
ref = list([x[1]] * x[0] for x in sequence)

t_din = Tuple[Uint[16], Uint[16]]


def test_pygears_sim():
    directed(drv(t=t_din, seq=sequence), f=replicate, ref=ref)
    sim()


def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    directed(
        drv(t=t_din, seq=sequence),
        f=replicate(sim_cls=partial(SimSocket, run=True)),
        ref=ref)

    sim(outdir=prepare_result_dir())


def test_verilate_sim():
    skip_ifndef('VERILATOR_ROOT')
    directed(
        drv(t=t_din, seq=sequence), f=replicate(sim_cls=SimVerilated), ref=ref)

    sim(outdir=prepare_result_dir())


def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=t_din, seq=sequence),
        f=replicate(sim_cls=partial(SimSocket, run=True)),
        ref=replicate(name='ref_model'))

    sim(outdir=prepare_result_dir())


def test_verilate_cosim():
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=t_din, seq=sequence),
        f=replicate(sim_cls=SimVerilated),
        ref=replicate(name='ref_model'))

    sim(outdir=prepare_result_dir())
