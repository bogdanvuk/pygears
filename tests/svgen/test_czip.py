from nose import with_setup

from pygears import Intf, bind, clear, registry
from pygears.typing import Queue, Uint, Unit
from pygears.svgen import svgen
from pygears.common.czip import zip_sync, zip_cat
from pygears.svgen.generate import svgen_module
from utils import equal_on_nonspace

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
    assign din0.ready = all_valid && (dout0.ready || !din0_eot_aligned);
    assign dout1.valid = out_valid;
    assign dout1.data = din1_s;
    assign din1.ready = all_valid && (dout1.ready || !din1_eot_aligned);



endmodule
"""


@with_setup(clear)
def test_two_inputs_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]), outsync=False)

    bind('SVGenFlow', registry('SVGenFlow')[:-1])
    assert equal_on_nonspace(svgen_module(svgen()['zip_sync']),
                             test_two_inputs_no_outsync_ref)


test_two_inputs_simple_no_outsync_ref = """
module zip_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // u4 (4)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // u4 (4)

);


    logic all_valid;
    assign all_valid   = din0.valid && din1.valid;

    assign dout0.valid = all_valid;
    assign dout0.data = din0.data;
    assign din0.ready = dout0.dready;
    assign dout1.valid = all_valid;
    assign dout1.data = din1.data;
    assign din1.ready = dout1.dready;


endmodule
"""


@with_setup(clear)
def test_two_inputs_simple_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]), outsync=False)

    bind('SVGenFlow', registry('SVGenFlow')[:-1])
    assert equal_on_nonspace(svgen_module(svgen()['zip_sync']),
                             test_two_inputs_simple_no_outsync_ref)


test_two_inputs_simple_ref = """
module zip_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // u4 (4)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // u4 (4)

);

    dti #(.W_DATA(6)) din0_if(); // [u3]^3 (6)
    dti #(.W_DATA(4)) din1_if(); // u4 (4)

    logic all_valid;
    assign all_valid   = din0.valid && din1.valid;

    assign dout0_if.valid = all_valid;
    assign dout0_if.data = din0.data;
    assign din0.ready = dout0_if.dready;
    assign dout1_if.valid = all_valid;
    assign dout1_if.data = din1.data;
    assign din1.ready = dout1_if.dready;


    zip_sync_syncguard syncguard (
        .clk(clk),
        .rst(rst),
        .din0(din0_if),
        .din1(din1_if),
        .dout0(dout0),
        .dout1(dout1)
    );

endmodule
"""


@with_setup(clear)
def test_two_inputs_simple():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])
    sv_zip_sync, sv_syncguard = svgen_module(svgen()['zip_sync'])
    assert equal_on_nonspace(sv_zip_sync,
                             test_two_inputs_simple_ref)


test_two_inputs_ref = """
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

    assign dout0_if.valid = out_valid;
    assign dout0_if.data = din0_s;
    assign din0.ready = all_valid && (dout0_if.ready || !din0_eot_aligned);
    assign dout1_if.valid = out_valid;
    assign dout1_if.data = din1_s;
    assign din1.ready = all_valid && (dout1_if.ready || !din1_eot_aligned);


    zip_sync_syncguard syncguard (
        .clk(clk),
        .rst(rst),
        .din0(din0_if),
        .din1(din1_if),
        .dout0(dout0),
        .dout1(dout1)
    );


endmodule
"""


@with_setup(clear)
def test_two_inputs():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])
    sv_zip_sync, sv_syncguard = svgen_module(svgen()['zip_sync'])
    assert equal_on_nonspace(sv_zip_sync,
                             test_two_inputs_ref)


test_zip_cat_ref = """
module zip_cat
(
    input clk,
    input rst,
    dti.consumer din0, // [u4]^5 (9)
    dti.consumer din1, // u1 (1)
    dti.consumer din2, // [u3]^3 (6)
    dti.consumer din3, // [Unit] (1)
    dti.producer dout // [(u4, u1, u3)]^5 (13)

);
    typedef struct packed { // [u4]^5
        logic [4:0] eot; // u5
        logic [3:0] data; // u4
    } din0_t;

    typedef struct packed { // u1
        logic [0:0] data; // u1
    } din1_t;

    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din2_t;

    typedef struct packed { // [Unit]
        logic [0:0] eot; // u1
    } din3_t;

    typedef struct packed { // [(u4, u1, u3)]^5
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

    assign dout_s.eot = din0_s.eot;
    assign dout_s.data = { din2_s.data, din1_s.data, din0_s.data };

    logic  all_valid;
    logic  handshake;
    assign all_valid = din0.valid && din1.valid && din2.valid && din3.valid;
    assign handshake = dout.valid & dout.ready;
    assign dout.valid = all_valid;
    assign dout.data = dout_s;

    assign din0.ready = handshake;
    assign din1.ready = handshake;
    assign din2.ready = handshake;
    assign din3.ready = handshake;



endmodule
"""


@with_setup(clear)
def test_zip_cat():
    zip_cat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])
    assert equal_on_nonspace(svgen_module(svgen()['zip_cat']),
                             test_zip_cat_ref)


# @with_setup(clear)
# def test_general():
#     zip_sync(
#         Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
#         Intf(Queue[Unit, 1]))

#     bind('SVGenFlow', registry('SVGenFlow')[:-1])

#     svtop = svgen()
#     # from pygears.util.print_hier import print_hier
#     # print_hier(svtop)
#     print(svtop['zip_sync'].get_module(TemplateEnv()))
#     print(svtop['zip_sync/unzip'].get_module(TemplateEnv()))
#     # print(svtop['zip_sync/sieve_2'].get_module(TemplateEnv()))
#     # print(svtop['zip_sync/czip'].get_module(TemplateEnv()))
#     # print(svtop['zip_sync/czip/sieve_0_3_1_2_4'].get_module(TemplateEnv()))

#     # assert equal_on_nonspace(svtop['zip_sync'].get_module(TemplateEnv()),
#     #                          test_zip_sync_general_sv_ref)


# bind('ErrReportLevel', 0)
# test_general()
