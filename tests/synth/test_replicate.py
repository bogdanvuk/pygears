from pygears import Intf
from pygears.cookbook import replicate
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 12, 'ffs': 16})
def test_replicate():
    replicate(Intf(Tuple[Uint[16], Uint[16]]))
