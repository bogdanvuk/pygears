import pytest

from pygears.cookbook import qlen_cnt
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Uint


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('cnt_one_more', [True, False])
def test_directed_lvl1(tmpdir, sim_cls, din_delay, dout_delay, cnt_one_more):
    t_din = Queue[Uint[16]]

    seq = [list(range(2)), list(range(8)), list(range(5))]
    if cnt_one_more:
        ref = [1, 1, 1]
    else:
        ref = [0, 0, 0]
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qlen_cnt(sim_cls=sim_cls, cnt_one_more=cnt_one_more),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('cnt_one_more', [True, False])
def test_directed_lvl2(tmpdir, sim_cls, din_delay, dout_delay, cnt_one_more):
    t_din = Queue[Uint[16], 2]

    seq = [[list(range(2)), list(range(8))], [list(range(5))]]
    if cnt_one_more:
        ref = [2, 1]
    else:
        ref = [1, 0]
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qlen_cnt(sim_cls=sim_cls, cnt_one_more=cnt_one_more),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('cnt_one_more', [True, False])
def test_directed_lvl3_2(tmpdir, sim_cls, din_delay, dout_delay, cnt_one_more):
    t_din = Queue[Uint[16], 3]

    seq = [[[list(range(2)), list(range(8))], [list(range(5))]],
           [[[1], [1, 2, 3], [4, 4, 4, 4, 4]]]]
    if cnt_one_more:
        ref = [2, 1]
    else:
        ref = [1, 0]
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=qlen_cnt(sim_cls=sim_cls, cnt_one_more=cnt_one_more, cnt_lvl=2),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)
