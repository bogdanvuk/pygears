from pygears import Intf
from pygears.cookbook import qcnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_qnct():
    qcnt(Intf(Queue[Uint[8], 3]))
