from pygears import Intf
from pygears.cookbook import alternate_queues
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_2_inputs():
    alternate_queues(Intf(Queue[Uint[8], 2]), Intf(Queue[Uint[8], 2]))
