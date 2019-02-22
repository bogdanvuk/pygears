from pygears import Intf
from pygears.typing import Uint, Array
from pygears.util.test_utils import synth_check
from pygears.common.serialize import TDin, serialize


@synth_check({'logic luts': 19, 'ffs': 3})
def test_unsigned():
    serialize(Intf(Array[Uint[16], 4]))


@synth_check({'logic luts': 15, 'ffs': 4})
def test_unsigned_alternative():
    serialize(Intf(TDin[Uint[8], 4, 4]))
