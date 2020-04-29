from pygears.lib import delay, directed, drv, const
from pygears.typing import Uint, Unit
from pygears.sim import sim

def test_basic(sim_cls):
    directed(
        f=const(sim_cls=sim_cls, val=Uint[4](5)),
        ref=[5, 5, 5, 5])

    sim(timeout=4)

def test_unit(sim_cls):
    directed(
        f=const(sim_cls=sim_cls, val=Unit()),
        ref=[Unit(), Unit(), Unit(), Unit()])

    sim(timeout=4)
