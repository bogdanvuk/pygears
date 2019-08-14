from pygears.lib import sdp
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Tuple, Uint


def test_directed(tmpdir, sim_cls):
    wr_addr_data = [(i, i * 2) for i in range(4)]
    rd_addr = list(range(4))
    rd_data = [i * 2 for i in range(4)]

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=wr_addr_data),
             drv(t=Uint[3], seq=rd_addr) | delay_rng(1, 1),
             f=sdp(sim_cls=sim_cls, depth=4),
             ref=rd_data)

    sim(outdir=tmpdir)
