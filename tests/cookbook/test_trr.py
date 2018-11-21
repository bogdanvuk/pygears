import random
from functools import partial

from pygears.cookbook.trr import trr
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import prepare_result_dir, skip_ifndef

t_din = Queue[Uint[16]]


def test_directed(tmpdir, sim_cls):
    directed(
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        drv(t=t_din, seq=[list(range(9)), list(range(3))]),
        f=trr(sim_cls=sim_cls),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

    sim(outdir=tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')

    din_num = 3

    stim = []
    for i in range(din_num):
        stim.append(
            drv(t=t_din,
                seq=[
                    list(range(random.randint(1, 10))),
                    list(range(random.randint(1, 10)))
                ]))

    verif(*stim, f=trr(sim_cls=sim_cls), ref=trr(name='ref_model'))

    sim(outdir=tmpdir)


def test_socket_cosim_rand():
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    din_num = 3

    cons = []
    for i in range(din_num):
        cons.append(
            create_constraint(t_din, f'din{i}', eot_cons=['data_size == 10']))

    stim = []
    for i in range(din_num):
        stim.append(drv(t=t_din, seq=rand_seq(f'din{i}', 30)))

    verif(
        *stim,
        f=trr(sim_cls=partial(SimSocket, run=True)),
        ref=trr(name='ref_model'))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
