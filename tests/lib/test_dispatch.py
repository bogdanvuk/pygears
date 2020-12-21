from pygears import sim
from pygears.lib import delay_rng, directed, dispatch, drv
from pygears.typing import Tuple, Uint


def test_basic():
    seq = [(0, 0x1), (1, 0x2), (2, 0x4), (3, 0x3), (4, 0x6), (5, 0x5), (6, 0x7), (7, 0x0)]
    ref = [
        [0, 3, 5, 6],
        [1, 3, 4, 6],
        [2, 4, 5, 6],
    ]

    directed(drv(t=Tuple[Uint[8], Uint[3]], seq=seq),
             f=dispatch(__sim__='verilator'),
             delays=[delay_rng(0, 3) for _ in range(3)],
             ref=ref)

    sim()
