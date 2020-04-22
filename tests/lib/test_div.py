from pygears.lib import add, drv, verif
from pygears.sim import sim
from pygears.typing import Fixp, Int, Uint


def test_unsigned(cosim_cls):
    a_seq = [0, 5, 14, 15]
    b = 6

    verif(drv(t=Uint[4], seq=a_seq),
          f=add(b=b, sim_cls=cosim_cls),
          ref=add(b=b, name='ref_model'))

    sim()


def test_signed(cosim_cls):
    a_seq = [-8, -1, 0, 1, 7]
    b = 5

    verif(drv(t=Int[4], seq=a_seq),
          f=add(b=b, sim_cls=cosim_cls),
          ref=add(b=b, name='ref_model'))

    sim()


def test_fixp(cosim_cls):
    a_seq = [-8., -1, 0, 1, 7]
    b = Fixp[1, 5](-0.125)

    verif(drv(t=Fixp[4, 6], seq=a_seq),
          f=add(b=b, sim_cls=cosim_cls),
          ref=add(b=b, name='ref_model'))

    sim()
