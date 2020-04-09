import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib import group
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, synth_check


def get_dut(dout_delay):
    @gear
    def decoupled(*din):
        return din | group | decouple

    if dout_delay == 0:
        return decoupled
    return group


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('cfg_delay', [0, 5])
def test_queue_directed(tmpdir, sim_cls, din_delay, dout_delay, cfg_delay):
    t_din = Queue[Uint[16]]
    t_cfg = Uint[16]

    dut = get_dut(dout_delay)
    directed(drv(t=t_din,
                 seq=[
                     list(range(5)),
                     list(range(3)),
                     list(range(2)),
                     list(range(3)),
                     list(range(8))
                 ])
             | delay_rng(din_delay, din_delay),
             drv(t=t_cfg, seq=[2, 3]) | delay_rng(cfg_delay, cfg_delay),
             f=dut(sim_cls=sim_cls),
             ref=[[list(range(5)), list(range(3))],
                  [list(range(2)),
                   list(range(3)),
                   list(range(8))]],
             delays=[delay_rng(dout_delay, dout_delay)])
    sim(resdir=tmpdir)

# from pygears.sim.modules import SimVerilated
# from pygears import config
# config['debug/trace'] = ['*']
# test_queue_directed('/tools/home/tmp/qfilt', SimVerilated, 0, 0, 1)

@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('cfg_delay', [0, 5])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay, cfg_delay):
    t_din = Uint[16]
    t_cfg = Uint[8]

    dut = get_dut(dout_delay)
    directed(drv(t=t_din, seq=list(range(15)))
             | delay_rng(din_delay, din_delay),
             drv(t=t_cfg, seq=[1, 2, 3, 4, 5])
             | delay_rng(cfg_delay, cfg_delay),
             f=dut(sim_cls=sim_cls),
             ref=[
                 list(range(0, 1)),
                 list(range(1, 3)),
                 list(range(3, 6)),
                 list(range(6, 10)),
                 list(range(10, 15))
             ],
             delays=[delay_rng(dout_delay, dout_delay)])
    sim(resdir=tmpdir)


@formal_check()
def test_formal():
    group(Intf(Queue[Uint[8]]), Intf(Uint[3]))


@synth_check({'logic luts': 17, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    group(Intf(Queue[Uint[16]]), Intf(Uint[16]))


@synth_check({'logic luts': 50, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    group(Intf(Queue[Uint[16]]), Intf(Uint[16]))
