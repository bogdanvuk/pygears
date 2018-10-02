import random
from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.trr_dist import trr_dist
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.svrand import SVRandSocket, create_queue_cons, qrand
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import prepare_result_dir, skip_ifndef

t_trr_dist = Queue[Uint[16], 2]
seq = [[list(range(random.randint(1, 10))),
        list(range(random.randint(1, 5)))],
       [list(range(random.randint(1, 20))),
        list(range(random.randint(1, 7)))]]
ref0 = [seq[0][0], seq[1][0]]
ref1 = [seq[0][1], seq[1][1]]


@with_setup(clear)
def test_pygears_sim():
    directed(
        drv(t=t_trr_dist, seq=seq), f=trr_dist(dout_num=2), ref=[ref0, ref1])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    num = 2
    verif(
        drv(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=partial(SimSocket, run=True), dout_num=num),
        ref=trr_dist(name='ref_model', dout_num=num))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_verilator_cosim():
    skip_ifndef('VERILATOR_ROOT')
    num = 2
    verif(
        drv(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=SimVerilated, dout_num=num),
        ref=trr_dist(name='ref_model', dout_num=num))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim_rand():
    skip_ifndef('SIM_SOCKET_TEST')

    dout_num = 2
    cons = []
    cons.extend(
        create_queue_cons(
            t_trr_dist,
            'din',
            eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=t_trr_dist, seq=qrand('din', 30)),
        f=trr_dist(sim_cls=partial(SimSocket, run=True), dout_num=dout_num),
        ref=trr_dist(name='ref_model', dout_num=dout_num))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
