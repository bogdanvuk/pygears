from pygears import Intf
from pygears.cookbook.rng import py_rng
from pygears.typing import Tuple, Uint, Int
from pygears.util.test_utils import formal_check

# TODO : hierarchy must be avoided for verilog (so py_rng, not rng)


@formal_check()
def test_basic_unsigned():
    py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))


@formal_check()
def test_cnt_steps_unsigned():
    py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]), cnt_steps=True)


@formal_check()
def test_incr_cnt_steps_unsigned():
    py_rng(
        Intf(Tuple[Uint[4], Uint[4], Uint[2]]),
        cnt_steps=True,
        incr_steps=True)


# @formal_check()
# def test_basic_signed():
#     py_rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))

# @formal_check()
# def test_cnt_steps_signed():
#     py_rng(Intf(Tuple[Int[4], Int[6], Uint[2]]), cnt_steps=True)

# @formal_check()
# def test_incr_cnt_steps_signed():
#     py_rng(
#         Intf(Tuple[Int[4], Int[6], Uint[2]]), cnt_steps=True, incr_steps=True)
