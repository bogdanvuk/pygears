import pytest
from pygears import Intf
from pygears.typing import Queue, Tuple, Uint
from pygears.lib import czip, zip_sync

from pygears.sim import sim
from pygears.lib.delay import delay_rng
from pygears.lib.verif import drv, verif


def test_general():
    iout = czip(Intf(Uint[1]), Intf(Queue[Uint[2], 1]),
                Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Uint[3], Uint[4]], 5]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim_one_queue(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(drv(t=Uint[8], seq=list(range(10)))
          | delay_rng(din_delay, din_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din_delay, din_delay),
          f=czip(sim_cls=cosim_cls),
          ref=czip(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(resdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim_both_queue(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din_delay, din_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din_delay, din_delay),
          f=czip(sim_cls=cosim_cls),
          ref=czip(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(resdir=tmpdir)


@pytest.mark.parametrize('din0_delay', [0, 1])
@pytest.mark.parametrize('din1_delay', [0, 1])
@pytest.mark.parametrize('dout0_delay', [0, 1])
@pytest.mark.parametrize('dout1_delay', [0, 1])
def test_cosim_zipsync_one_queue(tmpdir, cosim_cls, din0_delay, din1_delay,
                                 dout0_delay, dout1_delay):
    verif(drv(t=Uint[8], seq=list(range(10)))
          | delay_rng(din0_delay, din0_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din1_delay, din1_delay),
          f=zip_sync(sim_cls=cosim_cls),
          ref=zip_sync(name='ref_model'),
          delays=[
              delay_rng(dout0_delay, dout0_delay),
              delay_rng(dout1_delay, dout1_delay)
          ])

    sim(resdir=tmpdir)


@pytest.mark.parametrize('din0_delay', [0, 1])
@pytest.mark.parametrize('din1_delay', [0, 1])
@pytest.mark.parametrize('dout0_delay', [0, 1])
@pytest.mark.parametrize('dout1_delay', [0, 1])
def test_cosim_zipsync_both_queue(tmpdir, cosim_cls, din0_delay, din1_delay,
                                  dout0_delay, dout1_delay):
    verif(drv(t=Queue[Uint[8], 2], seq=[[list(range(10)) for _ in range(2)]])
          | delay_rng(din0_delay, din0_delay),
          drv(t=Queue[Uint[8], 2], seq=[[list(range(10)) for _ in range(2)]])
          | delay_rng(din1_delay, din1_delay),
          f=zip_sync(sim_cls=cosim_cls),
          ref=zip_sync(name='ref_model'),
          delays=[
              delay_rng(dout0_delay, dout0_delay),
              delay_rng(dout1_delay, dout1_delay)
          ])

    sim(resdir=tmpdir)
