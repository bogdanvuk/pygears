
module cart_cart_cat
(
    input logic clk,
    input logic rst,
    dti.consumer din0, // [u4] (5)
    dti.consumer din1, // u1 (1)
    dti.producer dout // [(u4, u1)] (6)

);
    typedef struct packed { // [u4]
        logic [0:0] eot; // u1
        logic [3:0] data; // u4
    } din0_t;

    typedef logic [0:0] din1_t; // u1

    typedef struct packed { // (u4, u1)
        logic [0:0] f1; // u1
        logic [3:0] f0; // u4
    } dout_data_t;

    typedef struct packed { // [(u4, u1)]
        logic [0:0] eot; // u1
        dout_data_t data; // (u4, u1)
    } dout_t;

    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;
    assign dout.data = dout_s;


    assign dout_s.eot = { din0_s.eot };
    assign dout_s.data = { din1_s, din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid && dout.ready;

    assign din0.ready = din0.valid ? handshake : dout.ready;
    assign din1.ready = din1.valid ? handshake : dout.ready;



endmodule
