from nose import with_setup

from pygears import Intf, Uint, bind, clear, Queue
from pygears.svgen import svgen, svgen_connect, svgen_inst
from pygears.svgen.generate import TemplateEnv

from . import equal_on_nonspace

test_uint_ref = """
module sieve_0v2_7_8v10
(
    input clk,
    input rst,
    dti.consumer din, // u10 (10)
    dti.producer dout // u5 (5)

);
   assign dout.data = {din.data[9:8], din.data[7:7], din.data[1:0]};
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
"""


@with_setup(clear)
def test_uint():
    iout = Intf(Uint[10])[:2, 7, 8:]

    assert iout.dtype == Uint[5]

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()

    assert equal_on_nonspace(svtop['sieve_0v2_7_8v10'].get_module(
        TemplateEnv()), test_uint_ref)


test_queue_ref = """
module sieve_0v2_3_5v7
(
    input clk,
    input rst,
    dti.consumer din, // [u2]^6 (8)
    dti.producer dout // [u2]^4 (6)

);
   assign dout.data = {din.data[7:6], din.data[4:4], din.data[2:0]};
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
"""


@with_setup(clear)
def test_queue():
    iout = Intf(Queue[Uint[2], 6])[:2, 3, 5:]

    assert iout.dtype == Queue[Uint[2], 4]

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()

    assert equal_on_nonspace(svtop['sieve_0v2_3_5v7'].get_module(
        TemplateEnv()), test_queue_ref)
