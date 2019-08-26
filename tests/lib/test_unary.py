from pygears.typing import Uint
from pygears.lib import drv, unary, check
from pygears.sim import sim


def test_directed(tmpdir, sim_cls):

    drv(t=Uint[4], seq=[0, 1, 2, 3, 4, 5, 6, 7, 8]) \
        | unary(sim_cls=sim_cls) \
        | check(ref=[0x00, 0x01, 0x03, 0x07, 0x0f, 0x1f, 0x3f, 0x7f, 0xff])

    sim(tmpdir)
