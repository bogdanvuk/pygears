from pygears import Intf
from pygears.cookbook import trr_dist
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_trr_dist():
    trr_dist(Intf(Queue[Uint[16], 2]), dout_num=2)


@formal_check()
def test_lvl_2():
    trr_dist(Intf(Queue[Uint[16], 3]), dout_num=3, lvl=2)
