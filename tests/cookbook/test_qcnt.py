from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.qcnt import qcnt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import prepare_result_dir, skip_ifndef
import random

t_din = Queue[Uint[16], 3]
seq = [[[
    list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))
], [list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))]]]
ref = [
    list(
        range(sum(len(x) for x in seq[0][0]) + sum(len(x) for x in seq[0][1])))
]


@with_setup(clear)
def test_pygears_sim():
    directed(drv(t=t_din, seq=seq), f=qcnt(lvl=t_din.lvl), ref=ref)

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=partial(SimSocket, run=True), lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_verilate_cosim():
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=SimVerilated, lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))

    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_cosim_rand():
    skip_ifndef('SIM_SOCKET_TEST')

    cons = []
    cons.append(
        create_constraint(
            t_din, 'din', eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=t_din, seq=rand_seq('din', 30)),
        f=qcnt(sim_cls=partial(SimSocket, run=True), lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
