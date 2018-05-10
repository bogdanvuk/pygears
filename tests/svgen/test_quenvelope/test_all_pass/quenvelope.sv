/*
    None
*/

module quenvelope
(
    input clk,
    input rst,
    dti.consumer din, // [u1]^2 (3)
    dti.producer dout // [()]^2 (2)

);
    typedef struct packed { // [u1]^2
        logic [1:0] out_eot; // u2
        logic [0:0] data; // u1
    } din_t;

    typedef struct packed { // [()]^2
        logic [1:0] out_eot; // u2
    } dout_t;


    din_t din_s;
    dout_t dout_s;

    assign din_s = din.data;


    assign dout_s.out_eot = din_s.out_eot;
    assign dout.data = dout_s;

    assign din.ready = dout.ready;
    assign dout.valid = din.valid;


endmodule