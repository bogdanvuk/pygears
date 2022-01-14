from pygears import gear, reg, sim
from pygears.sim import cosim
from pygears.lib import drv, shred, mul
from pygears.typing import Int
from pygears.util.test_utils import websim_check

@websim_check
def test_in_port_intf_name_overlap(sim_cls):
    @gear
    def dut(row):
        row = row | mul(2)
        return row | mul(2)

    drv(t=Int[8], seq=list(range(8))) \
        | dut(sim_cls=sim_cls) \
        | shred
