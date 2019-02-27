from pygears import Intf
from pygears.cookbook import take
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_take():
    take(Intf(Queue[Tuple[Uint[16], Uint[16]]]))


@formal_check()
def test_qtake():
    take(Intf(Queue[Tuple[Uint[16], Uint[16]], 2]))
