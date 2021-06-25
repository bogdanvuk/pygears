import pytest
from pygears.sim import cosim

from pygears.lib import sdp
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Tuple, Uint


def test_directed(sim_cls):
    wr_addr_data = [(i, i * 2) for i in range(4)]
    rd_addr = list(range(4))
    rd_data = [i * 2 for i in range(4)]

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=wr_addr_data),
             drv(t=Uint[3], seq=rd_addr) | delay_rng(1, 1),
             f=sdp(sim_cls=sim_cls, depth=4, latency=2),
             ref=rd_data)

    sim()


def test_sim_prefil(sim_cls):
    rd_addr = list(range(4))

    mem = {i: 2 * i for i in rd_addr}
    rd_data = [mem[i] for i in rd_addr]

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=[]),
             drv(t=Uint[3], seq=rd_addr),
             f=sdp(sim_cls=sim_cls, depth=4, mem=mem),
             ref=rd_data)

    sim()


@pytest.mark.parametrize('latency', [1, 3, 4, 7])
def test_directed(latency):
    print(f'Latency: {latency}')
    wr_addr_data = [(i, i * 2) for i in range(4)]
    rd_addr = list(range(4))
    rd_data = [i * 2 for i in range(4)]

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=wr_addr_data),
             drv(t=Uint[3], seq=rd_addr) | delay_rng(latency, latency),
             f=sdp(depth=4, latency=latency),
             ref=rd_data)

    cosim('/sdp', 'verilator')
    sim()


@pytest.mark.parametrize('latency', [1, 3, 4, 7])
def test_directed_full_read(latency):
    print(f'Latency: {latency}')
    depth = 8
    mem = list(range(depth))

    rd_addr = list(range(8))
    rd_data = list(range(8))

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=[]),
             drv(t=Uint[3], seq=rd_addr),
             f=sdp(depth=8, latency=latency, mem=mem),
             ref=rd_data)

    cosim('/sdp', 'verilator')
    sim()


@pytest.mark.parametrize('latency', [1, 3, 4, 7])
def test_directed_dout_throtle(latency):
    print(f'Latency: {latency}')
    depth = 8
    mem = list(range(depth))

    rd_addr = list(range(8))
    rd_data = list(range(8))

    directed(drv(t=Tuple[Uint[3], Uint[5]], seq=[]),
             drv(t=Uint[3], seq=rd_addr),
             f=sdp(depth=8, latency=latency, mem=mem),
             delays=[delay_rng(4, 4)],
             ref=rd_data)

    cosim('/sdp', 'verilator')
    sim()
