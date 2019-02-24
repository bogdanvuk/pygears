from pygears import Intf
from pygears.cookbook import qlen_cnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 4, 'ffs': 16})
def test_qlen_cnt():
    qlen_cnt(Intf(Queue[Uint[16], 3]))
