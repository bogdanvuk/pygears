import pytest

from pygears import Intf, gear
from pygears.lib import decoupler, mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Int, Queue, Uint, bitw
from pygears.util.test_utils import formal_check


def get_dut(dout_delay):
    @gear
    def decoupled(*din):
        return din | mux | decoupler

    if dout_delay == 0:
        return decoupled
    return mux


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_uint_directed(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
    t_ctrl = Uint[4]
    t_din = Uint[8]

    dut = get_dut(dout_delay)
    directed(drv(t=t_ctrl, seq=[0, 1, 2])
             | delay_rng(cfg_delay, cfg_delay),
             drv(t=t_din, seq=[5])
             | delay_rng(din_delay, din_delay),
             drv(t=t_din, seq=[6])
             | delay_rng(din_delay, din_delay),
             drv(t=t_din, seq=[7])
             | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls),
             ref=[(5, 0), (6, 1), (7, 2)],
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
@pytest.mark.parametrize('branches', [2, 5, 7])
def test_mapped_directed(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay,
                         branches):

    t_ctrl = Uint[bitw(branches - 1)]

    ref = [(i, i) for i in range(branches)]

    mapping = {}
    for i in range(branches):
        mapping[i] = (i + 1) if (i + 1) < branches else 0

    ctrl = list(range(branches))

    seqs = [[(i - 1) if (i - 1) >= 0 else (branches - 1)]
            for i in range(branches)]

    drvs = [
        drv(t=Uint[s[0] + 1], seq=s) | delay_rng(din_delay, din_delay)
        for s in seqs
    ]

    # print(mapping)
    # print(seqs)
    # print(ctrl)
    # print(ref)

    directed(drv(t=t_ctrl, seq=ctrl) | delay_rng(cfg_delay, cfg_delay),
             *drvs,
             f=mux(mapping=mapping, sim_cls=sim_cls),
             delays=[delay_rng(dout_delay, dout_delay)],
             ref=ref)

    sim(outdir=tmpdir)


# test_mapped_directed('/tools/home/tmp', None, 0, 0, 0, 5)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_diff_inputs(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
    t_ctrl = Uint[2]
    t_din0 = Uint[5]
    t_din1 = Int[10]
    t_din2 = Queue[Uint[8]]

    dut = get_dut(dout_delay)
    directed(drv(t=t_ctrl, seq=[0, 1, 2])
             | delay_rng(cfg_delay, cfg_delay),
             drv(t=t_din0, seq=[5])
             | delay_rng(din_delay, din_delay),
             drv(t=t_din1, seq=[6])
             | delay_rng(din_delay, din_delay),
             drv(t=t_din2, seq=[[8]])
             | delay_rng(din_delay, din_delay),
             f=dut(sim_cls=sim_cls),
             ref=[(5, 0), (6, 1), (264, 2)],
             delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


# @formal_check(assumes=[
#     's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
#     's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
# ])
# def test_formal():
#     mux(Intf(Uint[4]), Intf(Uint[8]), Intf(Uint[8]))

# @formal_check(assumes=[
#     's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
#     's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
# ])
# def test_queue_formal():
#     mux(Intf(Uint[4]), Intf(Queue[Uint[8], 3]), Intf(Queue[Uint[8], 3]))
