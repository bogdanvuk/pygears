from functools import partial


from pygears.common.serialize import serialize, TDin
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Array, Uint
from pygears.util.test_utils import prepare_result_dir, skip_ifndef


def test_pygears_sim():
    brick_size = 4
    seq_list = [1, 2, 3, 4]
    directed(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize,
        ref=sorted(seq_list * brick_size))

    sim()


def test_pygears_sim_active():
    no = 4
    directed(
        drv(t=TDin[16, no, 4], seq=[((3, ) * no, 7)]),
        f=serialize,
        ref=[[3, 3, 3]])

    sim()


def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    brick_size = 4
    seq_list = [1, 2, 3]
    directed(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=partial(SimSocket, run=True)),
        ref=sorted(seq_list * brick_size))

    sim()


def test_verilate_sim(tmpdir):
    skip_ifndef('VERILATOR_ROOT')
    brick_size = 4
    seq_list = [1, 2, 3, 4]
    directed(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=SimVerilated),
        ref=sorted(seq_list * brick_size))

    sim(outdir=tmpdir)


def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    brick_size = 4
    seq_list = [1, 2, 3, 4]
    verif(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=partial(SimSocket, run=True)),
        ref=serialize(name='ref_model'))

    sim()
