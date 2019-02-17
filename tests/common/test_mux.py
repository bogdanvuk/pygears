import pytest

from pygears.common import mux
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Uint


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


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('cfg_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_queue_directed(tmpdir, sim_cls, din_delay, cfg_delay, dout_delay):
    t_ctrl = Uint[2]
    t_din = Queue[Uint[8]]

    directed(
        drv(t=t_ctrl, seq=[2, 1, 0, 0, 2, 1])
        | delay_rng(cfg_delay, cfg_delay),
        drv(t=t_din, seq=[[1, 2, 3], [4, 5, 6]])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=[[7, 8], [1, 2]])
        | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=[[2], [3]])
        | delay_rng(din_delay, din_delay),
        f=mux(sim_cls=sim_cls),
        ref=[(258, 2), (7, 1), (264, 1), (1, 0), (2, 0), (259, 0), (4, 0),
             (5, 0), (262, 0), (259, 2), (1, 1), (258, 1)],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)