from nose import with_setup

from pygears import Intf, Queue, Uint, clear, bind, Unit
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.common import czip
from pygears.svgen.generate import TemplateEnv
from . import equal_on_nonspace

test_czip_general_sv_ref = """
module czip
(
    input clk,
    input rst,
    dti_s_if.consumer din0, // u1 (1)
    dti_s_if.consumer din1, // [Unit] (1)
    dti_s_if.consumer din2, // [u3]^3 (6)
    dti_s_if.consumer din3, // [u4]^5 (9)
    dti_s_if.producer dout // [(u1, u3, u4)]^5 (13)

);


    typedef struct packed { // u1
        logic [0:0] data; // u1
    } din0_t;
    typedef struct packed { // [Unit]
        logic [0:0] eot; // u1
    } din1_t;
    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din2_t;
    typedef struct packed { // [u4]^5
        logic [4:0] eot; // u5
        logic [3:0] data; // u4
    } din3_t;
    typedef struct packed { // [(u1, u3, u4)]^5
        logic [4:0] eot; // u5
        logic [7:0] data; // u8
    } dout_t;

    din0_t din0_s;
    din1_t din1_s;
    din2_t din2_s;
    din3_t din3_s;
    dout_t dout_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;
    assign din2_s = din2.data;
    assign din3_s = din3.data;

    assign dout_s.eot = din1_s.eot | din2_s.eot | din3_s.eot;
    assign dout_s.data = { din3_s.data, din2_s.data, din0_s.data };

    logic din1_eot_aligned;
    assign din1_eot_aligned = (din1_s.eot==dout_s.eot[0:0]);
    logic din2_eot_aligned;
    assign din2_eot_aligned = (din2_s.eot==dout_s.eot[2:0]);
    logic din3_eot_aligned;
    assign din3_eot_aligned = (din3_s.eot==dout_s.eot[4:0]);

    logic all_valid;
    logic all_aligned;
    logic  handshake;
    assign all_valid = din0.valid & din1.valid & din2.valid & din3.valid;
    assign all_aligned = din1_eot_aligned & din2_eot_aligned & din3_eot_aligned;
    assign handshake = dout.valid & dout.ready;
    assign dout.valid = all_valid & all_aligned;
    assign dout.data = dout_s;

    assign din0.ready = handshake;
    assign din1.ready = all_valid & (all_aligned ? dout.ready : !din1_eot_aligned);
    assign din2.ready = all_valid & (all_aligned ? dout.ready : !din2_eot_aligned);
    assign din3.ready = all_valid & (all_aligned ? dout.ready : !din3_eot_aligned);

endmodule
"""


@with_setup(clear)
def test_general():
    czip(
        Intf(Uint[1]), Intf(Queue[Unit, 1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Uint[4], 5]))

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['czip'].get_module(TemplateEnv()),
                             test_czip_general_sv_ref)
