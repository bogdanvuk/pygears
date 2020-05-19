import pytest
import itertools

from pygears.lib import parallelize
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Array, Uint, Bool
from pygears.util.test_utils import get_decoupled_dut


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('size', [1, 4, 9])
def test_array(cosim_cls, din_delay, dout_delay, size):
    ref = [list(range(i * size, (i + 1) * size)) for i in range(255 // size)]

    dut = get_decoupled_dut(dout_delay, parallelize(t=Array[Uint[8], size]))
    directed(drv(t=Uint[8], seq=itertools.chain(*ref)),
             f=dut(name='dut', sim_cls=cosim_cls),
             ref=ref,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim()

# test_array(None, 0, 0, 4)



@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_uint(cosim_cls, din_delay, dout_delay):
    size = 8
    ref = [Uint[size](0x11), Uint[size](0x22), Uint[size](0x33)]

    dut = get_decoupled_dut(dout_delay, parallelize(t=Uint[size]))
    directed(drv(t=Bool, seq=itertools.chain(*ref)),
             f=dut(name='dut', sim_cls=cosim_cls),
             ref=ref,
             delays=[delay_rng(dout_delay, dout_delay)])

    sim()
