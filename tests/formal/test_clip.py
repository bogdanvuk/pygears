from pygears import Intf
from pygears.cookbook import clip
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_clip():
    clip(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
