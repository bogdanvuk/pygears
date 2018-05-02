from nose import with_setup

from pygears import Intf, clear, bind, registry
from pygears.typing import Queue, Uint, Unit
from pygears.svgen import svgen
from pygears.common.cart import cart
from pygears.svgen.generate import svgen_module
from utils import equal_on_nonspace

test_two_queue_inputs_ref = """
module cart
(
    input clk,
    input rst,
    dti.consumer din0, // [u4]^2 (6)
    dti.consumer din1, // [Unit] (1)
    dti.producer dout // [(u4, Unit)]^3 (7)

);
    typedef struct packed { // [u4]^2
        logic [1:0] eot; // u2
        logic [3:0] data; // u4
    } din0_t;

    typedef struct packed { // [Unit]
        logic [0:0] eot; // u1
    } din1_t;

    typedef struct packed { // [(u4, Unit)]^3
        logic [2:0] eot; // u3
        logic [3:0] data; // u4
    } dout_t;


    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;

    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout_s.eot = { din0_s.eot, din1_s.eot };
    assign dout_s.data = { din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid && dout.ready;
    assign dout.data = dout_s;

    assign din0.ready = handshake && (&din1_s.eot);
    assign din1.ready = handshake;



endmodule
"""


@with_setup(clear)
def test_two_queue_inputs():
    cart(Intf(Queue[Uint[4], 2]), Intf(Queue[Unit, 1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    assert equal_on_nonspace(svgen_module(svgen()['cart']),
                             test_two_queue_inputs_ref)


test_two_inputs_first_queue_ref = """
module cart
(
    input clk,
    input rst,
    dti.consumer din0, // [u4] (5)
    dti.consumer din1, // u1 (1)
    dti.producer dout // [(u4, u1)] (6)

);
    typedef struct packed { // [u4]
        logic [0:0] eot; // u1
        logic [3:0] data; // u4
    } din0_t;

    typedef struct packed { // u1
        logic [0:0] data; // u1
    } din1_t;

    typedef struct packed { // [(u4, u1)]
        logic [0:0] eot; // u1
        logic [4:0] data; // u5
    } dout_t;


    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;

    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout_s.eot = { din0_s.eot };
    assign dout_s.data = { din1_s.data, din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid && dout.ready;
    assign dout.data = dout_s;

    assign din0.ready = handshake && 1;
    assign din1.ready = handshake;



endmodule
    """


@with_setup(clear)
def test_two_inputs_first_queue():
    cart(Intf(Queue[Uint[4], 1]), Intf(Uint[1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    assert equal_on_nonspace(svgen_module(svgen()['cart']),
                             test_two_inputs_first_queue_ref)


test_two_inputs_second_queue_ref = """
module cart
(
    input clk,
    input rst,
    dti.consumer din0, // u1 (1)
    dti.consumer din1, // [u4] (5)
    dti.producer dout // [(u1, u4)] (6)

);
    typedef struct packed { // u1
        logic [0:0] data; // u1
    } din0_t;

    typedef struct packed { // [u4]
        logic [0:0] eot; // u1
        logic [3:0] data; // u4
    } din1_t;

    typedef struct packed { // [(u1, u4)]
        logic [0:0] eot; // u1
        logic [4:0] data; // u5
    } dout_t;


    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;

    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout_s.eot = { din1_s.eot };
    assign dout_s.data = { din1_s.data, din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid && dout.ready;
    assign dout.data = dout_s;

    assign din0.ready = handshake && (&din1_s.eot);
    assign din1.ready = handshake;



endmodule
"""


@with_setup(clear)
def test_two_inputs_second_queue():
    cart(Intf(Uint[1]), Intf(Queue[Uint[4], 1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    assert equal_on_nonspace(svgen_module(svgen()['cart']),
                             test_two_inputs_second_queue_ref)


# bind('ErrReportLevel', 0)
# test_two_inputs_second_queue()

# @with_setup(clear)
# def test_general():
#     cart_sync(
#         Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
#         Intf(Queue[Unit, 1]))

#     bind('SVGenFlow', registry('SVGenFlow')[:-1])

#     svtop = svgen()
#     # from pygears.util.print_hier import print_hier
#     # print_hier(svtop)
#     print(svtop['cart_sync'].get_module(TemplateEnv()))
#     print(svtop['cart_sync/unzip'].get_module(TemplateEnv()))
#     # print(svtop['cart_sync/sieve_2'].get_module(TemplateEnv()))
#     # print(svtop['cart_sync/czip'].get_module(TemplateEnv()))
#     # print(svtop['cart_sync/czip/sieve_0_3_1_2_4'].get_module(TemplateEnv()))

#     # assert equal_on_nonspace(svtop['cart_sync'].get_module(TemplateEnv()),
#     #                          test_cart_sync_general_sv_ref)

# bind('ErrReportLevel', 0)
# test_general()
