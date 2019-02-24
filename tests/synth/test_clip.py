from pygears import Intf
from pygears.cookbook import clip
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 11, 'ffs': 17})
def test_clip():
    clip(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
