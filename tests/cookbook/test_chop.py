import random
from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.chop import chop
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.svrand import (SVRandSocket, create_queue_cons,
                                       create_type_cons, qrand, svrand)
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import prepare_result_dir, skip_ifndef

t_din = Queue[Uint[16]]
t_cfg = Uint[16]


def get_stim():
    cfg_seq = []
    din_seq = []
    cfg_num = random.randint(2, 10)
    for i in range(cfg_num):
        cfg_seq.append(random.randint(1, 10))
        din_seq.append(list(range(random.randint(1, 10))))

    return [drv(t=t_din, seq=din_seq), drv(t=t_cfg, seq=cfg_seq)]


@with_setup(clear)
def test_pygears_sim():
    directed(
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        drv(t=t_cfg, seq=[2, 3]),
        f=chop,
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])

    sim()


@with_setup(clear)
def test_verilator_cosim():
    skip_ifndef('VERILATOR_ROOT')

    stim = get_stim()
    verif(*stim, f=chop(sim_cls=SimVerilated), ref=chop(name='ref_model'))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')

    stim = get_stim()
    verif(
        *stim,
        f=chop(sim_cls=partial(SimSocket, run=True)),
        ref=chop(name='ref_model'))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim_rand():
    skip_ifndef('SIM_SOCKET_TEST')

    cnt = 5

    cons = []
    cons.extend(create_queue_cons(t_din, 'din', eot_cons=['data_size < 20']))
    cons.append(create_type_cons(t_cfg, 'cfg', cons=['cfg < 20']))

    stim = []
    stim.append(drv(t=t_din, seq=qrand('din', cnt)))
    stim.append(drv(t=t_cfg, seq=svrand('cfg', cnt)))

    verif(
        *stim,
        f=chop(sim_cls=partial(SimSocket, run=True)),
        ref=chop(name='ref_model'))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
