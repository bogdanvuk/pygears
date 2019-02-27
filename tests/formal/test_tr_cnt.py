from pygears import Intf
from pygears.cookbook import tr_cnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_tr_cnt():
    tr_cnt(Intf(Queue[Uint[8]]), Intf(Uint[3]))
