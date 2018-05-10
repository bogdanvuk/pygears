from nose import with_setup

from pygears import Intf, clear
from pygears.common.cart import cart
from pygears.typing import Queue, Uint, Unit
from utils import svgen_check


@with_setup(clear)
@svgen_check(['cart.sv'])
def test_two_queue_inputs():
    cart(Intf(Queue[Uint[4], 2]), Intf(Queue[Unit, 1]))


@with_setup(clear)
@svgen_check(['cart.sv'])
def test_two_inputs_first_queue():
    cart(Intf(Queue[Uint[4], 1]), Intf(Uint[1]))


@with_setup(clear)
@svgen_check(['cart.sv'])
def test_two_inputs_second_queue():
    cart(Intf(Uint[1]), Intf(Queue[Uint[4], 1]))
