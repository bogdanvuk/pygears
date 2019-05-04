import random
from functools import partial

import pytest

from pygears import Intf
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.qcnt import qcnt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.cookbook.verif import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, skip_ifndef, synth_check

T_DIN = Queue[Uint[16], 3]
RANDOM_SEQ = [[[
    list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))
], [list(range(random.randint(1, 10))),
    list(range(random.randint(1, 10)))]]]
DIR_SEQ = [[[list(range(3)), list(range(5))], [list(range(1)),
                                               list(range(8))]]]


def get_ref(seq):
    num = 0
    for subseq in seq[0]:
        for subsubseq in subseq:
            num += len(subsubseq)

    return [list(range(1, num + 1))]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_golden(tmpdir, sim_cls, din_delay, dout_delay):
    seq = DIR_SEQ
    directed(
        drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=sim_cls, lvl=T_DIN.lvl),
        ref=get_ref(seq),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_random_golden(tmpdir, sim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = RANDOM_SEQ
    directed(
        drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(lvl=T_DIN.lvl, sim_cls=sim_cls),
        ref=get_ref(seq),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('lvl', range(1, T_DIN.lvl))
@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_directed_cosim(tmpdir, cosim_cls, lvl, din_delay, dout_delay):
    seq = DIR_SEQ
    verif(
        drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=cosim_cls, lvl=lvl),
        ref=qcnt(name='ref_model', lvl=lvl),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_random_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = RANDOM_SEQ
    verif(
        drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
        f=qcnt(sim_cls=cosim_cls, lvl=T_DIN.lvl),
        ref=qcnt(name='ref_model', lvl=T_DIN.lvl),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)


def test_socket_rand_cons(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cons = []
    cons.append(
        create_constraint(
            T_DIN, 'din', eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(
        drv(t=T_DIN, seq=rand_seq('din', 30)),
        f=qcnt(sim_cls=partial(SimSocket, run=True), lvl=T_DIN.lvl),
        ref=qcnt(name='ref_model', lvl=T_DIN.lvl))

    sim(outdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_lvl_1():
    qcnt(Intf(Queue[Uint[8], 3]))


@formal_check()
def test_lvl_2():
    qcnt(Intf(Queue[Uint[8], 3]), lvl=2)


@synth_check({'logic luts': 5, 'ffs': 16})
def test_synth():
    qcnt(Intf(Queue[Uint[8], 3]))
