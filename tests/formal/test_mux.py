from pygears import Intf
from pygears.common import mux
from pygears.typing import Uint
from pygears.util.test_utils import formal_check


@formal_check(disable={'din0': 'live', 'ctrl': 'live'})
def test_unsigned():
    mux(Intf(Uint[4]), Intf(Uint[8]))
