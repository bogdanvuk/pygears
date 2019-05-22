import random
from functools import partial

import pytest

from pygears import Intf
from pygears.cookbook.clip import clip
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.cookbook.verif import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, skip_ifndef, synth_check

T_DIN = Queue[Tuple[Uint[16], Uint[16]]]
T_DIN_SEP = Queue[Uint[16]]
T_CFG = Uint[16]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay):
    seq = []
    tmp = []
    for i in range(9):
        tmp.append((i, 2))
    seq.append(tmp)

    tmp = []
    for i in range(5):
        tmp.append((i, 3))
    seq.append(tmp)

    directed(drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
             f=clip(sim_cls=sim_cls),
             ref=[[0, 1],
                  list(range(2, 9)),
                  list(range(3)),
                  list(range(3, 5))],
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_directed_two_inputs(tmpdir, cosim_cls):
    verif(drv(t=T_DIN_SEP, seq=[list(range(9)), list(range(5))]),
          drv(t=T_CFG, seq=[2, 3]),
          f=clip(sim_cls=cosim_cls),
          ref=clip(name='ref_model'))

    sim(outdir=tmpdir)


def test_random(tmpdir, cosim_cls):
    skip_ifndef('RANDOM_TEST')

    cfg_seq = []
    din_seq = []
    cfg_num = random.randint(2, 10)
    for _ in range(cfg_num):
        cfg_seq.append(random.randint(1, 10))
        din_seq.append(list(range(random.randint(1, 10))))

    verif(drv(t=T_DIN_SEP, seq=din_seq),
          drv(t=T_CFG, seq=cfg_seq),
          f=clip(sim_cls=cosim_cls),
          ref=clip(name='ref_model'))

    sim(outdir=tmpdir)


def test_random_constrained(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cnt = 5
    cons = []
    cons.append(
        create_constraint(T_DIN_SEP, 'din', eot_cons=['data_size == 20']))
    cons.append(create_constraint(T_CFG, 'cfg', cons=['cfg < 20', 'cfg > 0']))

    stim = []
    stim.append(drv(t=T_DIN_SEP, seq=rand_seq('din', cnt)))
    stim.append(drv(t=T_CFG, seq=rand_seq('cfg', cnt)))

    verif(*stim,
          f=clip(sim_cls=partial(SimSocket, run=True)),
          ref=clip(name='ref_model'))

    sim(outdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_formal():
    clip(Intf(T_DIN))


@synth_check({'logic luts': 11, 'ffs': 17}, tool='vivado')
def test_synth_vivado():
    clip(Intf(T_DIN))


@synth_check({'logic luts': 37, 'ffs': 17}, tool='yosys')
def test_synth_yosys():
    clip(Intf(T_DIN))
