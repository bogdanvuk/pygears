from nose import with_setup

from pygears import Intf, clear
from pygears.common.mux import mux
from pygears.typing import Queue, Uint
from utils import svgen_check


@with_setup(clear)
@svgen_check([])
def test_two_inputs_simple():
    mux(Intf(Uint[1]), Intf(Uint[3]), Intf(Uint[5]))


@with_setup(clear)
@svgen_check([])
def test_two_inputs():
    mux(Intf(Uint[1]), Intf(Uint[3]), Intf(Queue[Uint[3], 3]))


@with_setup(clear)
@svgen_check([])
def test_two_queue_inputs():
    mux(Intf(Uint[1]), Intf(Queue[Uint[2], 2]), Intf(Queue[Uint[3], 3]))
