from nose import with_setup

from pygears import Intf, bind, clear, registry
from pygears.common import ccat
from pygears.svgen import svgen
from pygears.svgen.generate import svgen_module
from pygears.typing import Queue, Uint, Unit
from utils import equal_on_nonspace


test_general_ref = """
module ccat
(
    input clk,
    input rst,
    dti.consumer din0, // [u4]^5 (9)
    dti.consumer din1, // u1 (1)
    dti.consumer din2, // [u3]^3 (6)
    dti.consumer din3, // [Unit] (1)
    dti.producer dout // ([u4]^5, u1, [u3]^3, [Unit]) (17)

);

    logic  all_valid;
    logic  handshake;
    assign all_valid = din0.valid && din1.valid && din2.valid && din3.valid;
    assign handshake = dout.valid & dout.ready;

    assign dout.valid = all_valid;
    assign dout.data = { din3.data, din2.data, din1.data, din0.data };

    assign din0.ready = handshake;
    assign din1.ready = handshake;
    assign din2.ready = handshake;
    assign din3.ready = handshake;


endmodule
"""


@with_setup(clear)
def test_general():
    ccat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    assert equal_on_nonspace(svgen_module(svgen()['ccat']), test_general_ref)
