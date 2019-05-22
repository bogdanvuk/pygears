import pytest

from pygears import Intf
from pygears.cookbook import take
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check

T_DIN = Queue[Tuple[Uint[16], Uint[16]]]
T_DIN_SEP = Queue[Uint[16]]
T_QDIN_SEP = Queue[Uint[16], 2]
T_CFG = Uint[16]
T_QDIN = Queue[Tuple[Uint[16], Uint[16]], 2]


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
             f=take(sim_cls=sim_cls),
             ref=[[0, 1], [0, 1, 2]],
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_directed_two_inputs(tmpdir, cosim_cls):
    verif(drv(t=T_DIN_SEP, seq=[list(range(9)), list(range(5))]),
          drv(t=T_CFG, seq=[2, 3]),
          f=take(sim_cls=cosim_cls),
          ref=take(name='ref_model'))

    sim(outdir=tmpdir)


@pytest.mark.parametrize('delay', [0, 5])
def test_q_directed(tmpdir, sim_cls, delay):
    seq = []
    tmp = []
    for _ in range(9):
        sub = []
        for j in range(3):
            sub.append((j, 2))
        tmp.append(sub)
    seq.append(tmp)

    tmp = []
    for _ in range(5):
        sub = []
        for j in range(6):
            sub.append((j, 3))
        tmp.append(sub)
    seq.append(tmp)

    directed(drv(t=T_QDIN, seq=seq) | delay_rng(delay, delay),
             f=take(sim_cls=sim_cls),
             ref=[[list(range(3))] * 2, [list(range(6))] * 3])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('cfg_delay', [0, 5])
def test_q_directed_two_inputs(tmpdir, sim_cls, din_delay, cfg_delay):
    seq = []
    tmp = []
    for _ in range(9):
        sub = []
        for j in range(3):
            sub.append(j)
        tmp.append(sub)
    seq.append(tmp)

    tmp = []
    for _ in range(5):
        sub = []
        for j in range(6):
            sub.append(j)
        tmp.append(sub)
    seq.append(tmp)

    directed(drv(t=T_QDIN_SEP, seq=seq) | delay_rng(din_delay, din_delay),
             drv(t=T_CFG, seq=[2, 3]) | delay_rng(cfg_delay, cfg_delay),
             f=take(sim_cls=sim_cls),
             ref=[[list(range(3))] * 2, [list(range(6))] * 3])

    sim(outdir=tmpdir)


@formal_check()
def test_take_formal():
    take(Intf(T_DIN))


@formal_check()
def test_qtake_formal():
    take(Intf(T_QDIN))


@synth_check({'logic luts': 20, 'ffs': 17}, tool='vivado')
def test_take_vivado():
    take(Intf(T_DIN))


@synth_check({'logic luts': 82, 'ffs': 17}, tool='yosys')
def test_take_yosys():
    take(Intf(T_DIN))
