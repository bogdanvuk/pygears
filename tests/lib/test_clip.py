import random

import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib.clip import clip
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim, cosim
from pygears.sim.extens.randomization import randomize
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, skip_ifndef, synth_check

T_DIN = Queue[Tuple[Uint[16], Uint[16]]]
T_DIN_SEP = Queue[Uint[16]]
T_CFG = Uint[16]


def get_dut(dout_delay):
    @gear
    def decoupled(*din):
        return din | clip | decouple

    if dout_delay == 0:
        return decoupled
    return clip


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed(sim_cls, din_delay, dout_delay):
    seq = []
    tmp = []
    for i in range(9):
        tmp.append((i, 2))
    seq.append(tmp)

    tmp = []
    for i in range(5):
        tmp.append((i, 3))
    seq.append(tmp)

    dut = get_dut(dout_delay)
    directed(
        drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls),
        ref=[[0, 1], list(range(2, 9)),
             list(range(3)), list(range(3, 5))],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim()


def test_directed_two_inputs(cosim_cls):
    verif(
        drv(t=T_DIN_SEP, seq=[list(range(9)), list(range(5))]),
        drv(t=T_CFG, seq=[2, 3]),
        f=clip(sim_cls=cosim_cls),
        ref=clip(name='ref_model'))

    sim()


def test_random(cosim_cls):
    skip_ifndef('RANDOM_TEST')

    cfg_seq = []
    din_seq = []
    cfg_num = random.randint(2, 10)
    for _ in range(cfg_num):
        cfg_seq.append(random.randint(1, 10))
        din_seq.append(list(range(random.randint(1, 10))))

    verif(
        drv(t=T_DIN_SEP, seq=din_seq),
        drv(t=T_CFG, seq=cfg_seq),
        f=clip(sim_cls=cosim_cls),
        ref=clip(name='ref_model'))

    sim()


def test_random_constrained():
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cnt = 5

    # cons.append(randomize(T_CFG, 'cfg', cons=['cfg == 2']))

    stim = []
    stim.append(drv(t=T_DIN_SEP, seq=randomize(T_DIN_SEP, 'din', cnt=cnt)))
    stim.append(
        drv(t=T_CFG, seq=randomize(T_CFG, 'cfg', cons=['cfg < 20', 'cfg > 0'], cnt=cnt)))

    verif(*stim, f=clip, ref=clip(name='ref_model'))

    cosim('/clip', 'xsim', run=False)
    sim()

    # cosim('/clip', 'xsim', run=True)
    # sim(resdir=extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_formal():
    clip(Intf(T_DIN))


@synth_check({'logic luts': 11, 'ffs': 17}, tool='vivado')
def test_synth_vivado():
    clip(Intf(T_DIN))


@synth_check({'logic luts': 13, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    clip(Intf(T_DIN))
