import pytest

from pygears import Intf
from pygears.cookbook import tr_cnt
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, synth_check


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('cfg_delay', [0, 5])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay, cfg_delay):
    t_din = Queue[Uint[16]]
    t_cfg = Uint[16]

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


@formal_check()
def test_formal():
    tr_cnt(Intf(Queue[Uint[8]]), Intf(Uint[3]))


@synth_check({'logic luts': 11, 'ffs': 16})
def test_synth():
    tr_cnt(Intf(Queue[Uint[16]]), Intf(Uint[16]))
