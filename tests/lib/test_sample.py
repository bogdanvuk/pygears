from pygears.lib import delay, directed, sample, drv
from pygears.typing import Uint
from pygears.sim import sim

def test_sample(sim_cls):
    directed(
        drv(t=Uint[2], seq=[1, 2]) | delay(2),
        f=sample(sim_cls=sim_cls),
        ref=[1, 1, 1, 2])

    sim(timeout=7)
