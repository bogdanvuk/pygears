 
 


module cart_cart_sync
(
    input logic clk,
    input logic rst,
    dti.consumer din0, // [u4]^2 (6)
    dti.consumer din1, // [()] (1)
    dti.producer dout0, // [u4]^2 (6)
    dti.producer dout1 // [()] (1)

);
    typedef struct packed { // [u4]^2
        logic [1:0] eot; // u2
        logic [3:0] data; // u4
    } din0_t;

    typedef struct packed { // [()]
        logic [0:0] eot; // u1
    } din1_t;

    din0_t din0_s;
    din1_t din1_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;


  logic all_valid;
  assign all_valid   = din0.valid && din1.valid;

    assign dout0.valid = all_valid;
    assign dout0.data = din0.data;
    assign dout1.valid = all_valid;
    assign dout1.data = din1.data;

    assign din0.ready = din1.valid && din1.ready && (&din1_s.eot);
    assign din1.ready = dout1.valid && dout1.ready;


endmodule
