from pygears import Intf
from pygears.cookbook import trr
from pygears.typing import Queue, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 24, 'ffs': 2})
def test_trr():
    trr(Intf(Queue[Uint[16]]), Intf(Queue[Uint[16]]), Intf(Queue[Uint[16]]))
