from nose import with_setup

from pygears import Intf, Queue, Uint, clear, bind, Unit
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.common import zip_sync
from pygears.svgen.generate import TemplateEnv
from . import equal_on_nonspace

test_two_inputs_no_outsync_ref = """
module zip_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // [u4]^5 (9)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // [u4]^5 (9)

);
    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din0_t;

    typedef struct packed { // [u4]^5
        logic [4:0] eot; // u5
        logic [3:0] data; // u4
    } din1_t;


    din0_t din0_s;
    din1_t din1_s;

    assign din0_s = din0.data;
    assign din1_s = din1.data;


    dti #(.W_DATA(6)) din0_if(); // [u3]^3 (6)
    dti #(.W_DATA(9)) din1_if(); // [u4]^5 (9)

    logic all_valid;
    logic out_valid;
    logic out_ready;
    logic all_aligned;
    logic handshake;
    logic [2:0] din0_eot_overlap;
    logic din0_eot_aligned;
    logic [2:0] din1_eot_overlap;
    logic din1_eot_aligned;

    assign din0_eot_overlap = din0_s.eot[2:0];
    assign din1_eot_overlap = din1_s.eot[2:0];

    assign din0_eot_aligned = din0_eot_overlap >= din1_eot_overlap;
    assign din1_eot_aligned = din1_eot_overlap >= din0_eot_overlap;

    assign all_valid   = din0.valid && din1.valid;
    assign all_aligned = din0_eot_aligned && din1_eot_aligned;
    assign out_valid   = all_valid & all_aligned;

    assign dout0.valid = out_valid;
    assign dout0.data = din0_s;
    assign din0.ready = dout0.dready || !din0_eot_aligned;
    assign dout1.valid = out_valid;
    assign dout1.data = din1_s;
    assign din1.ready = dout1.dready || !din1_eot_aligned;

endmodule
"""


@with_setup(clear)
def test_two_inputs_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]), outsync=False)

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['zip_sync'].get_module(TemplateEnv()),
                             test_two_inputs_no_outsync_ref)
