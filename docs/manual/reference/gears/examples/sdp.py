from pygears.lib import sdp, check, drv, delay
from pygears.typing import Uint, Tuple

wr_addr_data = drv(t=Tuple[Uint[2], Uint[3]],
                   seq=[(0, 0), (1, 2), (2, 4), (3, 6)])
rd_addr = drv(t=Uint[2], seq=[0, 1, 2, 3]) | delay(1)

rd_addr \
    | sdp(wr_addr_data) \
    | check(ref=[0, 2, 4, 6])
