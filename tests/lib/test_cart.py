import pytest

from pygears import Intf
from pygears.typing import Uint, Queue, Tuple, Unit
from pygears.lib import cart, cart_sync

from pygears.sim import sim
from pygears.lib.delay import delay_rng
from pygears.lib.verif import drv, verif


def test_two():
    iout = cart(Intf(Queue[Unit, 3]), Intf(Uint[1]))

    assert iout.dtype == Queue[Tuple[Unit, Uint[1]], 3]


def test_multiple():
    iout = cart(Intf(Uint[1]), Intf(Queue[Uint[2], 1]), Intf(Queue[Unit, 3]),
                Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Unit, Uint[4]], 9]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(drv(t=Uint[8], seq=[0]) | delay_rng(din_delay, din_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din_delay, din_delay),
          f=cart(sim_cls=cosim_cls),
          ref=cart(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din0_delay', [0, 1])
@pytest.mark.parametrize('din1_delay', [0, 1])
@pytest.mark.parametrize('dout0_delay', [0, 1])
@pytest.mark.parametrize('dout1_delay', [0, 1])
def test_cosim_cartsync(tmpdir, cosim_cls, din0_delay, din1_delay, dout0_delay,
                        dout1_delay):
    verif(drv(t=Uint[8], seq=[0]) | delay_rng(din0_delay, din0_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din1_delay, din1_delay),
          f=cart_sync(sim_cls=cosim_cls),
          ref=cart_sync(name='ref_model'),
          delays=[
              delay_rng(dout0_delay, dout0_delay),
              delay_rng(dout1_delay, dout1_delay)
          ])

    sim(outdir=tmpdir)
