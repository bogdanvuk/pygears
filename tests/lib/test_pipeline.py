import pytest

from pygears.lib import pipeline
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Uint


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_sim(din_delay, dout_delay):
    seq = list(range(1, 10))
    directed(drv(t=Uint[16], seq=seq) | delay_rng(din_delay, din_delay),
             f=pipeline(length=8),
             ref=seq,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim()


@pytest.mark.parametrize('din_delay', [0, 3])
@pytest.mark.parametrize('dout_delay', [0, 3])
def test_cosim(din_delay, dout_delay):
    from pygears.sim.modules import SimVerilated

    seq = list(range(1, 10))
    verif(drv(t=Uint[16], seq=seq) | delay_rng(0, din_delay),
          f=pipeline(name='dut', length=8),
          ref=pipeline(length=8, sim_cls=SimVerilated),
          delays=[delay_rng(0, dout_delay)],
          check_timing=True
          )

    sim()



@pytest.mark.parametrize('din_delay', [0, 3])
@pytest.mark.parametrize('dout_delay', [0, 3])
def test_cosim_feedback(din_delay, dout_delay):
    from pygears.sim.modules import SimVerilated

    seq = list(range(1, 10))
    verif(drv(t=Uint[16], seq=seq) | delay_rng(0, din_delay),
          f=pipeline(name='dut', length=8, feedback=True),
          ref=pipeline(length=8, feedback=True, sim_cls=SimVerilated),
          delays=[delay_rng(0, dout_delay)],
          check_timing=True
          )

    sim()
