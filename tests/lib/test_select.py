import pytest

from pygears.lib.delay import delay_rng
from pygears.lib.verif import drv
from pygears.sim import sim
from pygears.typing import Tuple, Uint


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('ctrl_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_tuple_uint_directed(sim_cls, din_delay, ctrl_delay,
                             dout_delay):
    from pygears.lib.verif import check

    t_ctrl = Uint[4]
    t_din = Tuple[Uint[8], Uint[8], Uint[8]]

    ctrl = drv(t=t_ctrl, seq=[0, 1, 2]) \
        | delay_rng(ctrl_delay, ctrl_delay)

    data = drv(t=t_din, seq=[(5, 6, 7), (5, 6, 7), (5, 6, 7)]) \
        | delay_rng(din_delay, din_delay)

    check(data[ctrl] | delay_rng(dout_delay, dout_delay), ref=[5, 6, 7])

    sim()
