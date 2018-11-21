import pytest
import random
from functools import partial

from pygears.cookbook.qcnt import qcnt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import skip_ifndef

t_din = Queue[Uint[16], 3]
random_seq = [[[
    list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))
], [list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))]]]
dir_seq = [[[list(range(3)), list(range(5))], [list(range(1)),
                                               list(range(8))]]]


def get_ref(seq):
    num = 0
    for subseq in seq[0]:
        for subsubseq in subseq:
            num += len(subsubseq)

    return [list(range(1, num + 1))]


def test_directed_golden(tmpdir, sim_cls):
    seq = dir_seq
    directed(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=sim_cls, lvl=t_din.lvl),
        ref=get_ref(seq))
    sim(outdir=tmpdir)


def test_random_golden(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')
    seq = random_seq
    directed(drv(t=t_din, seq=seq), f=qcnt(lvl=t_din.lvl), ref=get_ref(seq))
    sim(outdir=tmpdir)


@pytest.mark.parametrize('lvl', range(1, t_din.lvl))
def test_directed_cosim(tmpdir, sim_cls, lvl):
    seq = dir_seq
    verif(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=sim_cls, lvl=lvl),
        ref=qcnt(name='ref_model', lvl=lvl))
    sim(outdir=tmpdir)


def test_random_cosim(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')
    seq = random_seq
    verif(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=sim_cls, lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))
    sim(outdir=tmpdir)


def test_socket_rand_cons(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cons = []
    cons.append(
        create_constraint(
            t_din, 'din', eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=t_din, seq=rand_seq('din', 30)),
        f=qcnt(sim_cls=partial(SimSocket, run=True), lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl))

    sim(outdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])
