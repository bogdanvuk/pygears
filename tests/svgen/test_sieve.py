from pygears import Intf
from pygears.typing import Uint

from pygears.util.test_utils import svgen_check


@svgen_check(['sieve_0v2_7_8v10.sv'])
def test_uint():
    iout = Intf(Uint[10])[:2, 7, 8:]
    assert iout.dtype == Uint[5]


@svgen_check(['sieve_7v4.sv'])
def test_uint_downto_slice():
    iout = Intf(Uint[8])[7:4]
    assert iout.dtype == Uint[4]


@svgen_check(['sieve_7v4.sv'])
def test_uint_downto_slice_from_max():
    iout = Intf(Uint[8])[-1:4]
    assert iout.dtype == Uint[4]
