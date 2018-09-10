from nose import with_setup

from pygears import clear
from pygears.cookbook.chunk_concat import chunk_concat
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from pygears import GearDone, gear, bind
from pygears.typing import TLM
# from utils import skip_ifndef


@with_setup(clear)
def test_socket_sim(outdir):
    # skip_ifndef('SIM_SOCKET_TEST')
    directed(
        drv(t=Uint[16], seq=[6, 4, 6, 2, 1]),
        drv(t=Queue[Uint[16]], seq=[list(range(5))]),
        drv(t=Queue[Uint[16]], seq=[list(range(1, 6))]),
        drv(t=Queue[Uint[16]], seq=[list(range(2, 7))]),
        drv(t=Queue[Uint[16]], seq=[list(range(3, 8))]),
        drv(t=Queue[Uint[16]], seq=[list(range(4, 9))]),
        drv(t=Queue[Uint[16]], seq=[list(range(5, 10))]),
        # drv(t=Queue[Uint[16]], seq=[list(range(0))]),
        # drv(t=Queue[Uint[16]], seq=[list(range(0))]),
        drv(t=Queue[Uint[16]], seq=[list(range(6, 11))]),
        drv(t=Queue[Uint[16]], seq=[list(range(7, 12))]),
        f=chunk_concat(sim_cls=SimSocket, cnt_type=1,
                       chunk_size=4, pad=1),
        ref=[])

    bind('SVGenDebugIntfs', [
        '*',
    ])
    sim(outdir=outdir)


if __name__ == '__main__':
    test_socket_sim('/tools/home/bla')
