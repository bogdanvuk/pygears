from pygears import Intf
from pygears.common import dreg
from pygears.typing import Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_simple():
    dreg(Intf(Uint[16]))
