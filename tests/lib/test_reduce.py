import pytest
from pygears.util.test_utils import get_decoupled_dut
from pygears.lib import reduce, directed, drv
from pygears.typing import Uint, Queue
from pygears.sim import sim


def test_uint_directed(tmpdir, sim_cls):
    init = 0

    def add(x, y):
        return x + y

    directed(drv(t=Queue[Uint[8]], seq=[list(range(10)), list(range(2))]),
             drv(t=Uint[8], seq=[init, init]),
             f=reduce(f=add, sim_cls=sim_cls),
             ref=[sum(range(10), init), sum(range(2), init)])
    sim(outdir=tmpdir)
