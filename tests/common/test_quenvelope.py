from nose import with_setup

from pygears import clear, Intf
from pygears.typing import Uint, Queue, Unit
from pygears.common import quenvelope
from pygears.cookbook.verif import directed, verif
from pygears.sim.modules.drv import drv
from pygears.sim import sim


@with_setup(clear)
def test_skip():
    iout = quenvelope(Intf(Queue[Uint[1], 3]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]


@with_setup(clear)
def test_skip_sim():
    seq = [[list(range(1))], [list(range(1)), list(range(2))],
           [list(range(1)), list(range(2)),
            list(range(3))]]

    ref = [[Unit()], [Unit(), Unit()], [Unit(), Unit(), Unit()]]

    directed(
        drv(t=Queue[Uint[2], 3], seq=[seq]), f=quenvelope(lvl=2), ref=[ref])

    sim()


@with_setup(clear)
def test_all_pass():
    iout = quenvelope(Intf(Queue[Uint[1], 2]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]
