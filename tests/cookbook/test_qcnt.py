import random
from functools import partial

import pytest

from pygears.cookbook.delay import delay_rng
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


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_directed_golden(tmpdir, sim_cls, din_delay, dout_delay):
    seq = dir_seq
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=sim_cls, lvl=t_din.lvl),
        ref=get_ref(seq),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_random_golden(tmpdir, sim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = random_seq
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(lvl=t_din.lvl),
        ref=get_ref(seq),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('lvl', range(1, t_din.lvl))
@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_directed_cosim(tmpdir, cosim_cls, lvl, din_delay, dout_delay):
    seq = dir_seq
    verif(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=cosim_cls, lvl=lvl),
        ref=qcnt(name='ref_model', lvl=lvl),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_random_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = random_seq
    verif(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=cosim_cls, lvl=t_din.lvl),
        ref=qcnt(name='ref_model', lvl=t_din.lvl),
        delays=[delay_rng(dout_delay, dout_delay)])
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
