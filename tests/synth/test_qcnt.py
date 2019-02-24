from pygears import Intf
from pygears.cookbook import qcnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 5, 'ffs': 16})
def test_qnct():
    qcnt(Intf(Queue[Uint[8], 3]))
