from pygears import Intf
from pygears.cookbook import trr
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_unsigned():
    trr(Intf(Queue[Uint[16]]), Intf(Queue[Uint[16]]), Intf(Queue[Uint[16]]))
