from pygears import Intf
from pygears.cookbook import take
from pygears.typing import Tuple, Uint, Queue
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 20, 'ffs': 17})
def test_take():
    take(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
