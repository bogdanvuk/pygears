
module zip_cat
(
    input clk,
    input rst,
    dti.consumer din0, // [u4]^5 (9)
    dti.consumer din1, // u1 (1)
    dti.consumer din2, // [u3]^3 (6)
    dti.consumer din3, // [()] (1)
    dti.producer dout // [(u4, u1, u3, ())]^5 (13)

);
    typedef struct packed { // [u4]^5
        logic [4:0] eot; // u5
        logic [3:0] data; // u4
    } din0_t;


    typedef logic [0:0] din1_t; // u1


    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din2_t;


    typedef struct packed { // [()]
        logic [0:0] eot; // u1
    } din3_t;


    typedef struct packed { // (u4, u1, u3, ())
        logic [2:0] f2; // u3
        logic [0:0] f1; // u1
        logic [3:0] f0; // u4
    } dout_data_t;

    typedef struct packed { // [(u4, u1, u3, ())]^5
        logic [4:0] eot; // u5
        dout_data_t data; // (u4, u1, u3, ())
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
    assign dout_s.data = { din2_s.data, din1_s, din0_s.data };

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
