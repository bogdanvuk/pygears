
module cart
(
    input clk,
    input rst,
    dti.consumer din0, // [u4]^2 (6)
    dti.consumer din1, // [()] (1)
    dti.producer dout // [(u4, ())]^3 (7)

);
    typedef struct packed { // [u4]^2
        logic [1:0] eot; // u2
        logic [3:0] data; // u4
    } din0_t;


    typedef struct packed { // [()]
        logic [0:0] eot; // u1
    } din1_t;


    typedef struct packed { // (u4, ())
        logic [3:0] f0; // u4
    } dout_data_t;

    typedef struct packed { // [(u4, ())]^3
        logic [2:0] eot; // u3
        dout_data_t data; // (u4, ())
    } dout_t;



    din0_t din0_s;
    din1_t din1_s;
    dout_t dout_s;

    assign din0_s = din0.data;
    assign din1_s = din1.data;

    assign dout.data = dout_s;

    assign dout_s.eot = { din0_s.eot, din1_s.eot };
    assign dout_s.data = { din0_s.data };

    logic  handshake;
    assign dout.valid = din0.valid & din1.valid;
    assign handshake = dout.valid && dout.ready;

    assign din0.ready = handshake && (&din1_s.eot);
    assign din1.ready = handshake;



endmodule
