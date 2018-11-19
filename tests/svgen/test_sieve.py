from pygears import Intf
from pygears.typing import Queue, Uint

from pygears.util.test_utils import svgen_check


@svgen_check(['sieve_0v2_7_8v10.sv'])
def test_uint():
    iout = Intf(Uint[10])[:2, 7, 8:]
    assert iout.dtype == Uint[5]


# @svgen_check(['sieve_0v2_3_5v7.sv'])
# def test_queue():
#     iout = Intf(Queue[Uint[2], 6])[:2, 3, 5:]
#     assert iout.dtype == Queue[Uint[2], 4]
