from pygears import Intf
from pygears.cookbook import accumulator
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 67, 'ffs': 18})
def test_unsigned():
    accumulator(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
