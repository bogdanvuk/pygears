from nose import with_setup

from pygears import Intf, clear
from pygears.typing import Queue, Uint

from utils import svgen_check


@with_setup(clear)
@svgen_check(['sieve_0v2_7_8v10.sv'])
def test_uint():
    iout = Intf(Uint[10])[:2, 7, 8:]
    assert iout.dtype == Uint[5]


@with_setup(clear)
@svgen_check(['sieve_0v2_3_5v7.sv'])
def test_queue():
    iout = Intf(Queue[Uint[2], 6])[:2, 3, 5:]
    assert iout.dtype == Queue[Uint[2], 4]
