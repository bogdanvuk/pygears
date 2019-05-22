import pytest

from pygears import Intf
from pygears.common import mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Int, Queue, Uint
from pygears.util.test_utils import formal_check


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_uint_directed(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
    t_ctrl = Uint[4]
    t_din = Uint[8]

    directed(
        drv(t=t_ctrl, seq=[0, 1, 2])
        | delay_rng(cfg_delay, cfg_delay),
        drv(t=t_din, seq=[5])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=[6])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=[7])
        | delay_rng(din_delay, din_delay),
        f=mux(sim_cls=sim_cls),
        ref=[(5, 0), (6, 1), (7, 2)],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('cfg_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_queue_directed(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
#     t_ctrl = Uint[2]
#     t_din = Queue[Uint[8]]

#     directed(
#         drv(t=t_ctrl, seq=[2, 1, 0, 0, 2, 1])
#         | delay_rng(cfg_delay, cfg_delay),
#         drv(t=t_din, seq=[[1, 2, 3], [4, 5, 6]])
#         | delay_rng(din_delay, din_delay),
#         drv(t=t_din, seq=[[7, 8], [1, 2]])
#         | delay_rng(din_delay, din_delay),
#         drv(t=t_din, seq=[[2], [3]])
#         | delay_rng(din_delay, din_delay),
#         f=mux(sim_cls=sim_cls),
#         ref=[(258, 2), (7, 1), (264, 1), (1, 0), (2, 0), (259, 0), (4, 0),
#              (5, 0), (262, 0), (259, 2), (1, 1), (258, 1)],
#         delays=[delay_rng(dout_delay, dout_delay)])

#     sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_diff_inputs(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
    t_ctrl = Uint[2]
    t_din0 = Uint[5]
    t_din1 = Int[10]
    t_din2 = Queue[Uint[8]]

    directed(
        drv(t=t_ctrl, seq=[0, 1, 2])
        | delay_rng(cfg_delay, cfg_delay),
        drv(t=t_din0, seq=[5])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din1, seq=[6])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din2, seq=[[8]])
        | delay_rng(din_delay, din_delay),
        f=mux(sim_cls=sim_cls),
        ref=[(5, 0), (6, 1), (264, 2)],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@formal_check(assumes=[
    's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
    's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
])
def test_formal():
    mux(Intf(Uint[4]), Intf(Uint[8]), Intf(Uint[8]))


@formal_check(assumes=[
    's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
    's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
])
def test_queue_formal():
    mux(Intf(Uint[4]), Intf(Queue[Uint[8], 3]), Intf(Queue[Uint[8], 3]))
