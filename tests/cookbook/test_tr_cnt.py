import pytest

from pygears.cookbook import tr_cnt
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Uint

t_din = Queue[Uint[16]]
t_cfg = Uint[16]


@pytest.mark.parametrize('din_delay', [0, 1, 5])
@pytest.mark.parametrize('dout_delay', [0, 1, 5])
@pytest.mark.parametrize('cfg_delay', [0, 1, 5])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay, cfg_delay):
    directed(
        drv(t=t_din,
            seq=[
                list(range(5)),
                list(range(3)),
                list(range(2)),
                list(range(3)),
                list(range(8))
            ])
        | delay_rng(din_delay, din_delay),
        drv(t=t_cfg, seq=[2, 3]) | delay_rng(cfg_delay, cfg_delay),
        f=tr_cnt(sim_cls=sim_cls),
        ref=[[list(range(5)), list(range(3))],
             [list(range(2)), list(range(3)),
              list(range(8))]],
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(outdir=tmpdir)
