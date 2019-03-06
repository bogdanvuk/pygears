from pygears import Intf
from pygears.cookbook import qlen_cnt
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_cnt_lvl_1():
    qlen_cnt(Intf(Queue[Uint[16], 3]))


@formal_check()
def test_cnt_lvl_2():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_lvl=2)


@formal_check()
def test_cnt_lvl_1_cnt_more():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_one_more=True)


@formal_check()
def test_cnt_lvl_2_cnt_more():
    qlen_cnt(Intf(Queue[Uint[16], 3]), cnt_lvl=2, cnt_one_more=True)
