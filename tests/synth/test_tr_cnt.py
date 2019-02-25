from pygears import Intf
from pygears.cookbook import tr_cnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 11, 'ffs': 16})
def test_tr_cnt():
    tr_cnt(Intf(Queue[Uint[16]]), Intf(Uint[16]))
