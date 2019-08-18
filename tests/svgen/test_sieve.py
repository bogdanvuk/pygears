from pygears import Intf
from pygears.typing import Uint

from pygears.util.test_utils import hdl_check


@hdl_check(['sieve_0v2_7_8v10.sv'])
def test_uint():
    iout = Intf(Uint[10])[:2, 7, 8:]
    assert iout.dtype == Uint[5]


@hdl_check(['sieve_4v8.sv'])
def test_uint_downto_slice():
    iout = Intf(Uint[8])[7:4:-1]
    assert iout.dtype == Uint[4]


@hdl_check(['sieve_4v8.sv'])
def test_uint_downto_slice_from_max():
    iout = Intf(Uint[8])[-1:4:-1]
    assert iout.dtype == Uint[4]
