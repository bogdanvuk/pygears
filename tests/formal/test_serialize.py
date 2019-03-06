from pygears import Intf
from pygears.common.serialize import TDin, serialize
from pygears.typing import Array, Uint
from pygears.util.test_utils import formal_check


@formal_check()
def test_unsigned():
    serialize(Intf(Array[Uint[16], 4]))


@formal_check()
def test_unsigned_alternative():
    serialize(Intf(TDin[Uint[8], 4, 4]))
