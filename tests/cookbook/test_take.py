import pytest

from pygears.cookbook import take
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Tuple, Uint

t_din = Queue[Tuple[Uint[16], Uint[16]]]
t_din_sep = Queue[Uint[16]]
t_cfg = Uint[16]


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
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

    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=take(sim_cls=sim_cls),
        ref=[[0, 1], [0, 1, 2]],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_directed_two_inputs(tmpdir, cosim_cls):
    verif(
        drv(t=t_din_sep, seq=[list(range(9)), list(range(5))]),
        drv(t=t_cfg, seq=[2, 3]),
        f=take(sim_cls=cosim_cls),
        ref=take(name='ref_model'))

    sim(outdir=tmpdir)


@pytest.mark.parametrize('delay', [0, 1, 10])
def test_q_directed(tmpdir, sim_cls, delay):
    t_qdin = Queue[Tuple[Uint[16], Uint[16]], 2]

    seq = []
    tmp = []
    for i in range(9):
        sub = []
        for j in range(3):
            sub.append((j, 2))
        tmp.append(sub)
    seq.append(tmp)

    tmp = []
    for i in range(5):
        sub = []
        for j in range(6):
            sub.append((j, 3))
        tmp.append(sub)
    seq.append(tmp)

    directed(
        drv(t=t_qdin, seq=seq) | delay_rng(delay, delay),
        f=take(sim_cls=sim_cls),
        ref=[[list(range(3))] * 2, [list(range(6))] * 3])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('cfg_delay', [0, 1, 10])
def test_q_directed_two_inputs(tmpdir, sim_cls, din_delay, cfg_delay):
    t_din_sep = Queue[Uint[16], 2]
    t_cfg = Uint[16]
    seq = []
    tmp = []
    for i in range(9):
        sub = []
        for j in range(3):
            sub.append(j)
        tmp.append(sub)
    seq.append(tmp)

    tmp = []
    for i in range(5):
        sub = []
        for j in range(6):
            sub.append(j)
        tmp.append(sub)
    seq.append(tmp)

    directed(
        drv(t=t_din_sep, seq=seq) | delay_rng(din_delay, din_delay),
        drv(t=t_cfg, seq=[2, 3]) | delay_rng(cfg_delay, cfg_delay),
        f=take(sim_cls=sim_cls),
        ref=[[list(range(3))] * 2, [list(range(6))] * 3])

    sim(outdir=tmpdir)
