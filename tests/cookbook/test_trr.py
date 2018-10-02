import random
from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.trr import trr
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.svrand import SVRandSocket, create_queue_cons, qrand
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import prepare_result_dir, skip_ifndef

t_din = Queue[Uint[16]]


def get_din():
    return drv(
        t=t_din,
        seq=[
            list(range(random.randint(1, 10))),
            list(range(random.randint(1, 10)))
        ])


def get_stim(num=2):
    stim = []
    for i in range(num):
        stim.append(get_din())
    return stim


@with_setup(clear)
def test_pygears_sim():
    directed(
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        f=trr,
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')

    din_num = 3

    stim = get_stim(din_num)
    verif(
        *stim,
        f=trr(sim_cls=partial(SimSocket, run=True)),
        ref=trr(name='ref_model'))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_verilator_cosim():
    skip_ifndef('VERILATOR_ROOT')

    din_num = 3

    stim = get_stim(din_num)
    verif(*stim, f=trr(sim_cls=SimVerilated), ref=trr(name='ref_model'))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim_rand():
    skip_ifndef('SIM_SOCKET_TEST')

    din_num = 3

    cons = []
    for i in range(din_num):
        cons.extend(
            create_queue_cons(t_din, f'din{i}', eot_cons=['data_size == 10']))

    stim = []
    for i in range(din_num):
        stim.append(drv(t=t_din, seq=qrand(f'din{i}', 30)))

    verif(
        *stim,
        f=trr(sim_cls=partial(SimSocket, run=True)),
        ref=trr(name='ref_model'))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
