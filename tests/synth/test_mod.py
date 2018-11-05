from pygears import Intf
from pygears.common import mod
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 53, 'ffs': 0})
def test_unsigned_mod():
    mod(Intf(Tuple[Uint[10], Uint[4]]))
