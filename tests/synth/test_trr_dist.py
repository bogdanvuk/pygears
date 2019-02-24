from pygears import Intf
from pygears.cookbook import trr_dist
from pygears.typing import Queue, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 3, 'ffs': 1})
def test_trr_dist():
    trr_dist(Intf(Queue[Uint[16], 2]), dout_num=2)
