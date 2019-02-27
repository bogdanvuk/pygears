from pygears import Intf
from pygears.cookbook import chop
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_chop():
    chop(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
