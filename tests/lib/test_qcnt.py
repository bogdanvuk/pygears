import random
from functools import partial

import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib.delay import delay_rng
from pygears.lib.qcnt import qcnt
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import randomize, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
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


def get_dut(dout_delay):
    @gear
    def decoupled(din, *, lvl=0, init=1, w_out=16):
        return din \
            | qcnt(running=True, lvl=lvl, init=init, w_out=w_out) \
            | decouple

    if dout_delay == 0:
        return decoupled
    return qcnt(running=True)


def get_ref(seq):
    num = 0
    for subseq in seq[0]:
        for subsubseq in subseq:
            num += len(subsubseq)

    return [list(range(1, num + 1))]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_golden(sim_cls, din_delay, dout_delay):
    seq = DIR_SEQ
    dut = get_dut(dout_delay)
    directed(drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls),
             ref=get_ref(seq),
             delays=[delay_rng(dout_delay, dout_delay)])
    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_random_golden(sim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = RANDOM_SEQ
    dut = get_dut(dout_delay)
    directed(drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls),
             ref=get_ref(seq),
             delays=[delay_rng(dout_delay, dout_delay)])
    sim()


@pytest.mark.parametrize('lvl', range(1, 0))
@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_directed_cosim(cosim_cls, lvl, din_delay, dout_delay):
    seq = DIR_SEQ
    dut = get_dut(dout_delay)
    verif(drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls, lvl=lvl),
          ref=qcnt(name='ref_model', lvl=lvl),
          delays=[delay_rng(dout_delay, dout_delay)])
    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_random_cosim(cosim_cls, din_delay, dout_delay):
    skip_ifndef('RANDOM_TEST')
    seq = RANDOM_SEQ
    dut = get_dut(dout_delay)
    verif(drv(t=T_DIN, seq=seq) | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=qcnt(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])
    sim()


def test_socket_rand_cons():
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cons = []
    cons.append(
        randomize(T_DIN,
                          'din',
                          eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(drv(t=T_DIN, seq=rand_seq('din', 30)),
          f=qcnt(sim_cls=partial(SimSocket, run=True)),
          ref=qcnt(name='ref_model'))

    sim(extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_lvl_1():
    qcnt(Intf(Queue[Uint[8], 3]))


@formal_check()
def test_lvl_2():
    qcnt(Intf(Queue[Uint[8], 3]), lvl=2)


@synth_check({'logic luts': 4, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    qcnt(Intf(Queue[Uint[8], 3]))


@synth_check({'logic luts': 36, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    qcnt(Intf(Queue[Uint[8], 3]))
