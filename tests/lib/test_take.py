import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib import take
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check

T_DIN = Queue[Tuple[Uint[16], Uint[16]]]
T_DIN_SEP = Queue[Uint[16]]
T_QDIN_SEP = Queue[Uint[16], 2]
T_CFG = Uint[16]
T_QDIN = Queue[Tuple[Uint[16], Uint[16]], 2]


def get_dut(dout_delay):
    @gear
    def decoupled(din):
        return din | take | decouple

    if dout_delay == 0:
        return decoupled
    return take


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
        ref=[[0, 1], [0, 1, 2]],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim()


def test_directed_two_inputs(cosim_cls):
    verif(drv(t=T_DIN_SEP, seq=[list(range(9)), list(range(5))]),
          drv(t=T_CFG, seq=[2, 3]),
          f=take(sim_cls=cosim_cls),
          ref=take(name='ref_model'))

    sim()


@pytest.mark.parametrize('delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_q_directed(sim_cls, delay, dout_delay):
    seq1 = [[(j, 2) for j in range(3)] for _ in range(9)]
    seq2 = [[(j, 3) for j in range(6)] for _ in range(5)]

    seq = [seq1, seq2]

    dut = get_dut(dout_delay)
    directed(
        drv(t=T_QDIN, seq=seq) | delay_rng(delay, delay),
        f=dut(sim_cls=sim_cls),
        ref=[[list(range(3))] * 2, [list(range(6))] * 3],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('cfg_delay', [0, 5])
def test_q_directed_two_inputs(sim_cls, din_delay, cfg_delay):
    seq1 = [list(range(3)) for _ in range(9)]
    seq2 = [list(range(6)) for _ in range(5)]

    seq = [seq1, seq2]

    directed(drv(t=T_QDIN_SEP, seq=seq) | delay_rng(din_delay, din_delay),
             drv(t=T_CFG, seq=[2, 3]) | delay_rng(cfg_delay, cfg_delay),
             f=take(sim_cls=sim_cls),
             ref=[[list(range(3))] * 2, [list(range(6))] * 3])

    sim()


@formal_check()
def test_take_formal():
    take(Intf(T_DIN))


@formal_check()
def test_qtake_formal():
    take(Intf(T_QDIN))


@synth_check({'logic luts': 19, 'ffs': 16}, tool='vivado')
def test_take_vivado():
    take(Intf(T_DIN))


@synth_check({'logic luts': 17, 'ffs': 15}, tool='yosys')
def test_take_yosys():
    take(Intf(T_DIN))
