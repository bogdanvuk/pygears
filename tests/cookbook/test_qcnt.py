from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.qcnt import qcnt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.svrand import SVRandSocket, create_queue_cons, qrand
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import prepare_result_dir, skip_ifndef

t_din = Queue[Uint[16], 3]
seq = [[[list(range(9)), list(range(3))], [list(range(4)), list(range(7))]]]
ref = [list(range(23))]


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
    cons.extend(
        create_queue_cons(
            t_din, 'din', eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=t_din, seq=qrand('din', 30)),
        f=qcnt(sim_cls=partial(SimSocket, run=True), lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
