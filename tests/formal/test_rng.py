from pygears import Intf
from pygears.cookbook.rng import py_rng
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_basic_unsigned():
    # TODO : hierarchy must be avoided for verilog (so py_rng, not rng)
    py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))
