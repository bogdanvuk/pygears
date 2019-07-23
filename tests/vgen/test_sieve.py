from pygears import Intf
from pygears.typing import Uint

from pygears.util.test_utils import hdl_check


@hdl_check(['sieve_4v8.v'])
def test_uint_downto_slice():
    iout = Intf(Uint[8])[7:4]
    assert iout.dtype == Uint[4]
