from pygears import Intf
from pygears.cookbook import accumulator
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_unsigned():
    accumulator(Intf(Queue[Tuple[Uint[8], Uint[8]]]))
