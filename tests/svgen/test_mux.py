
from pygears import Intf
from pygears.common.mux import mux
from pygears.typing import Queue, Uint
from pygears.util.test_utils import svgen_check


@svgen_check([])
def test_two_inputs_simple():
    mux(Intf(Uint[1]), Intf(Uint[3]), Intf(Uint[5]))


@svgen_check([])
def test_two_inputs():
    mux(Intf(Uint[1]), Intf(Uint[3]), Intf(Queue[Uint[3], 3]))


@svgen_check([])
def test_two_queue_inputs():
    mux(Intf(Uint[1]), Intf(Queue[Uint[2], 2]), Intf(Queue[Uint[3], 3]))
