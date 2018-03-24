from nose import with_setup

from pygears import Intf, Queue, Uint, clear, bind, Unit
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.common import cart
from pygears.svgen.generate import TemplateEnv
from . import equal_on_nonspace

test_non_queue_and_queue_with_unit_ref = """
module cart
(
    input clk,
    input rst,
    dti_s_if.consumer din0, // [Unit]^3 (3)
    dti_s_if.consumer din1, // u1 (1)
    dti_s_if.producer dout // [u1]^3 (4)

);


    typedef struct packed { // [Unit]^3
        logic [2:0] eot; // u3
    } din0_t;
    typedef struct packed { // u1
        logic [0:0] data; // u1
    } din1_t;
    typedef struct packed { // [u1]^3
        logic [2:0] eot; // u3
        logic [0:0] data; // u1
    } dout_t;

    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout_s.eot = { din0_s.eot };
    assign dout_s.data = { din1_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid & dout.ready;
    assign dout.data = dout_s;

    assign din0.ready = handshake & dout.valid;
    assign din1.ready = handshake & dout.valid & (&din0_s.eot);

endmodule
"""


@with_setup(clear)
def test_non_queue_and_queue_with_unit():
    cart(Intf(Queue[Unit, 3]), Intf(Uint[1]))

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['cart'].get_module(TemplateEnv()),
                             test_non_queue_and_queue_with_unit_ref)


test_queue_and_queue_ref = """
module cart
(
    input clk,
    input rst,
    dti_s_if.consumer din0, // [u1]^3 (4)
    dti_s_if.consumer din1, // [u2] (3)
    dti_s_if.producer dout // [(u1, u2)]^4 (7)

);


    typedef struct packed { // [u1]^3
        logic [2:0] eot; // u3
        logic [0:0] data; // u1
    } din0_t;
    typedef struct packed { // [u2]
        logic [0:0] eot; // u1
        logic [1:0] data; // u2
    } din1_t;
    typedef struct packed { // [(u1, u2)]^4
        logic [3:0] eot; // u4
        logic [2:0] data; // u3
    } dout_t;

    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout_s.eot = { din1_s.eot, din0_s.eot };
    assign dout_s.data = { din1_s.data, din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid & dout.ready;
    assign dout.data = dout_s;

    assign din0.ready = handshake & dout.valid;
    assign din1.ready = handshake & dout.valid & (&din0_s.eot);

endmodule
"""


@with_setup(clear)
def test_queue_and_queue():
    cart(Intf(Queue[Uint[1], 3]), Intf(Queue[Uint[2]]))

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['cart'].get_module(TemplateEnv()),
                             test_queue_and_queue_ref)


test_general_ref = """
module cart(
    input clk,
    input rst,
    dti_s_if.consumer din0, // u1 (1)
    dti_s_if.consumer din1, // [Unit] (1)
    dti_s_if.consumer din2, // [u3]^3 (6)
    dti_s_if.consumer din3, // [u4]^5 (9)
    dti_s_if.producer dout // [(u1, u3, u4)]^9 (17)

);

    dti_s_if #(.W_DATA(2)) cart0_if_s(); // [u1] (2)

    dti_s_if #(.W_DATA(8)) cart1_if_s(); // [(u1, u3)]^4 (8)

    dti_s_if #(.W_DATA(17)) cart2_if_s(); // [((u1, u3), u4)]^9 (17)

    cart_cart0 cart0_i (
        .clk(clk),
        .rst(rst),
        .din0(din0),
        .din1(din1),
        .dout(cart0_if_s)
    );


    cart_cart1 cart1_i (
        .clk(clk),
        .rst(rst),
        .din0(cart0_if_s),
        .din1(din2),
        .dout(cart1_if_s)
    );


    cart_cart2 cart2_i (
        .clk(clk),
        .rst(rst),
        .din0(cart1_if_s),
        .din1(din3),
        .dout(cart2_if_s)
    );


    conv_dout conv_dout_i (
        .clk(clk),
        .rst(rst),
        .din(cart2_if_s),
        .dout(dout)
    );



endmodule
"""


@with_setup(clear)
def test_general():
    cart(
        Intf(Uint[1]), Intf(Queue[Unit, 1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Uint[4], 5]))

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['cart'].get_module(TemplateEnv()),
                             test_general_ref)
