import math
from pygears.lib import funclut, drv, check
from pygears.typing import Ufixp, Fixp
from pygears.sim import sim


def test_sqrt(sim_cls):
    drv(t=Ufixp[8, 8], seq=[0, 4, 64, 121]) \
        | funclut(f=math.sqrt, precision=4, sim_cls=sim_cls) \
        | check(ref=[0, 2, 8, 11])

    sim()


def test_sin(sim_cls):
    drv(t=Ufixp[2, 16], seq=[math.pi/12*i for i in range(12)]) \
        | funclut(f=math.sin, sim_cls=sim_cls) \
        | check(ref=[math.sin(math.pi/12*i) for i in range(12)], cmp=lambda x, y: abs(x-y) <= 1)

    sim()


def test_sin_signed(sim_cls):
    drv(t=Fixp[2, 16], seq=[math.pi/12*i for i in range(-6, 5)]) \
        | funclut(f=math.sin, sim_cls=sim_cls) \
        | check(ref=[math.sin(math.pi/12*i) for i in range(-6, 5)], cmp=lambda x, y: abs(x-y) <= 1)

    sim()
