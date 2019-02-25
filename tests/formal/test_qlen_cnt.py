from pygears import Intf
from pygears.cookbook import qlen_cnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_qlen_cnt():
    qlen_cnt(Intf(Queue[Uint[16], 3]))
