from pygears import Intf
from pygears.common import add
from pygears.typing import Int, Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 33, 'ffs': 0})
def test_unsigned_add():
    add(Intf(Uint[32]), Intf(Uint[32]))


@synth_check({'logic luts': 6, 'ffs': 0})
def test_signed_unsigned_add():
    add(Intf(Int[2]), Intf(Uint[4]))
