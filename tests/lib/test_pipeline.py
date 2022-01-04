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

@pytest.mark.parametrize('feedback', [True, False])
def test_cosim_all_init(feedback):
    from pygears.sim.modules import SimVerilated

    seq = list(range(1, 10))
    ref = [0] * 8 + seq
    directed(drv(t=Uint[16], seq=seq),
             f=pipeline(length=8, init=0, feedback=feedback, sim_cls=SimVerilated),
             ref=ref)

    sim()


@pytest.mark.parametrize('feedback', [True, False])
@pytest.mark.parametrize('length', [1, 3, 8])
@pytest.mark.parametrize('filled', [1, 0.5, 0.1])
def test_cosim_partial_init(feedback, length, filled):
    from pygears.sim.modules import SimVerilated


    seq = list(range(2*length))
    fill_length = min(1, int(length * filled))
    init = list(range(fill_length))

    ref = init + seq

    directed(drv(t=Uint[16], seq=seq),
             f=pipeline(length=length, init=init, feedback=feedback, sim_cls=SimVerilated),
             ref=ref)

    sim()
