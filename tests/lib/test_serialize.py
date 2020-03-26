import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib.serialize import serialize
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Array, Uint, Tuple, Any
from pygears.util.test_utils import formal_check, synth_check

TDin = Tuple[{'data': Array['t_data', 'no'], 'active': Uint['w_active']}]


def get_dut(dout_delay):
    @gear
    def decoupled(din):
        return din | serialize | decouple

    if dout_delay == 0:
        return decoupled
    return serialize


def test_directed(tmpdir, sim_cls):
    brick_size = 4
    seq_list = [1, 2, 3, 4]

    directed(drv(t=Array[Uint[16], brick_size],
                 seq=[(i, ) * brick_size for i in seq_list]),
             f=serialize(sim_cls=sim_cls),
             ref=[(i, ) * brick_size for i in seq_list])

    sim(tmpdir)


def test_directed_active(tmpdir, sim_cls):
    no = 4
    directed(drv(t=TDin[Uint[8], no, 4],
                 seq=[((8, ) * no, 3), ((2, ) * no, 4), ((1, ) * no, 1)]),
             f=serialize(sim_cls=sim_cls),
             ref=[[8] * 3, [2] * 4, [1]])

    sim(tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    brick_size = 4
    seq_list = [1, 2, 3, 4]

    dut = get_dut(dout_delay)
    verif(drv(t=Array[Uint[16], brick_size],
              seq=[(i, ) * brick_size
                   for i in seq_list]) | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=serialize(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim_active(tmpdir, cosim_cls, din_delay, dout_delay):
    no = 4
    dut = get_dut(dout_delay)
    verif(drv(t=TDin[Uint[8], no, 4],
              seq=[((8, ) * no, 3), ((2, ) * no, 4),
                   ((1, ) * no, 1)]) | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=serialize(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(tmpdir)


@formal_check()
def test_formal():
    serialize(Intf(Array[Uint[16], 4]))


@formal_check()
def test_formal_active():
    serialize(Intf(TDin[Uint[8], 4, 4]))


@synth_check({'logic luts': 20, 'ffs': 3}, tool='vivado')
def test_synth_vivado():
    serialize(Intf(Array[Uint[16], 4]))


@synth_check({'logic luts': 21, 'ffs': 2}, tool='yosys')
def test_synth_yosys():
    serialize(Intf(Array[Uint[16], 4]))


@synth_check({'logic luts': 16, 'ffs': 4}, tool='vivado')
def test_synth_active_vivado():
    serialize(Intf(TDin[Uint[8], 4, 4]))


@synth_check({'logic luts': 39, 'ffs': 4}, tool='yosys')
def test_synth_active_yosys():
    serialize(Intf(TDin[Uint[8], 4, 4]))
