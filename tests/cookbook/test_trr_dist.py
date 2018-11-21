import random
from functools import partial

from pygears.cookbook.trr_dist import trr_dist
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import skip_ifndef

t_trr_dist = Queue[Uint[16], 2]


def get_refs(seq):
    ref0 = [seq[0][0], seq[1][0]]
    ref1 = [seq[0][1], seq[1][1]]
    return [ref0, ref1]


def test_directed(tmpdir, sim_cls):
    seq = [[list(range(8)), list(range(2))], [list(range(1)), list(range(2))]]

    directed(
        drv(t=t_trr_dist, seq=seq),
        f=trr_dist(sim_cls=sim_cls, dout_num=2),
        ref=get_refs(seq))

    sim(outdir=tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')

    seq = [[
        list(range(random.randint(1, 10))),
        list(range(random.randint(1, 5)))
    ], [list(range(random.randint(1, 20))),
        list(range(random.randint(1, 7)))]]

    directed(
        drv(t=t_trr_dist, seq=seq),
        f=trr_dist(sim_cls=sim_cls, dout_num=2),
        ref=get_refs(seq))

    sim(outdir=tmpdir)


def test_socket_rand_cons(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cons = []
    cons.append(
        create_constraint(
            t_trr_dist,
            'din',
            eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=Queue[Uint[16], 2], seq=rand_seq('din', 30)),
        f=trr_dist(sim_cls=partial(SimSocket, run=True), dout_num=2),
        ref=trr_dist(name='ref_model', dout_num=2))

    sim(outdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])
