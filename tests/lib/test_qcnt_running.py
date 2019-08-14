import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib import qcnt
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, synth_check


def get_dut(dout_delay):
    @gear
    def decoupled(din, *, lvl=0, init=0, w_out=16):
        return din | qcnt(init=init, lvl=lvl, w_out=w_out) | decouple

    if dout_delay == 0:
        return decoupled
    return qcnt


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('init', [1, 0])
def test_directed_lvl1(tmpdir, sim_cls, din_delay, dout_delay, init):
    t_din = Queue[Uint[16]]

    seq = [list(range(2)), list(range(8)), list(range(5))]
    if init:
        ref = [1, 1, 1]
    else:
        ref = [0, 0, 0]
    dut = get_dut(dout_delay)
    directed(drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls, init=init, lvl=1),
             ref=ref,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('init', [1, 0])
def test_directed_lvl2(tmpdir, sim_cls, din_delay, dout_delay, init):
    t_din = Queue[Uint[16], 2]

    seq = [[list(range(2)), list(range(8))], [list(range(5))]]
    if init:
        ref = [2, 1]
    else:
        ref = [1, 0]
    dut = get_dut(dout_delay)
    directed(drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls, init=init, lvl=1),
             ref=ref,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
@pytest.mark.parametrize('init', [1, 0])
def test_directed_lvl3_2(tmpdir, sim_cls, din_delay, dout_delay, init):
    t_din = Queue[Uint[16], 3]

    seq = [[[list(range(2)), list(range(8))], [list(range(5))]],
           [[[1], [1, 2, 3], [4, 4, 4, 4, 4]]]]
    if init:
        ref = [2, 1]
    else:
        ref = [1, 0]
    dut = get_dut(dout_delay)
    directed(drv(t=t_din, seq=seq) | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls, init=init, lvl=2),
             ref=ref,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@formal_check()
def test_lvl_1():
    qcnt(Intf(Queue[Uint[16], 3]))


@formal_check()
def test_lvl_2():
    qcnt(Intf(Queue[Uint[16], 3]), lvl=2)


@formal_check()
def test_lvl_1_cnt_more():
    qcnt(Intf(Queue[Uint[16], 3]), init=1)


@formal_check()
def test_lvl_2_cnt_more():
    qcnt(Intf(Queue[Uint[16], 3]), lvl=2, init=1)


@synth_check({'logic luts': 4, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    qcnt(Intf(Queue[Uint[16], 3]))


@synth_check({'logic luts': 36, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    qcnt(Intf(Queue[Uint[16], 3]))
