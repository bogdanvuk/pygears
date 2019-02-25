from pygears import Intf
from pygears.cookbook import replicate
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_replicate():
    replicate(Intf(Tuple[Uint[16], Uint[16]]))
