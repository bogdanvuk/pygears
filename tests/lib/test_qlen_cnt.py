import pytest

from pygears import Intf, gear
from pygears.lib import decoupler
from pygears.cookbook import qlen_cnt
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, synth_check


def get_dut(dout_delay):
    @gear
    def decoupled(din, *, cnt_lvl=1, cnt_one_more=False, w_out=16):
        return din | qlen_cnt(
            cnt_one_more=cnt_one_more, cnt_lvl=cnt_lvl,
            w_out=w_out) | decoupler

    if dout_delay == 0:
        return decoupled
    return qlen_cnt


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
    dut = get_dut(dout_delay)
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls, cnt_one_more=cnt_one_more),
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
    dut = get_dut(dout_delay)
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls, cnt_one_more=cnt_one_more),
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
    dut = get_dut(dout_delay)
    directed(
        drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls, cnt_one_more=cnt_one_more, cnt_lvl=2),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@formal_check()
def test_cnt_lvl_1():
    qlen_cnt(Intf(Queue[Uint[16], 3]))


@formal_check()
def test_cnt_lvl_2():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_lvl=2)


@formal_check()
def test_cnt_lvl_1_cnt_more():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_one_more=True)


@formal_check()
def test_cnt_lvl_2_cnt_more():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_lvl=2, cnt_one_more=True)


@synth_check({'logic luts': 4, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    qlen_cnt(Intf(Queue[Uint[16], 3]))


@synth_check({'logic luts': 36, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    qlen_cnt(Intf(Queue[Uint[16], 3]))
