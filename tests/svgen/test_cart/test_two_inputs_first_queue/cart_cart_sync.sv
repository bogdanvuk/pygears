 
 


module cart_cart_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u4] (5)
    dti.consumer din1, // u1 (1)
    dti.producer dout0, // [u4] (5)
    dti.producer dout1 // u1 (1)

);
    typedef struct packed { // [u4]
        logic [0:0] eot; // u1
        logic [3:0] data; // u4
    } din0_t;

    typedef logic [0:0] din1_t; // u1

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

    assign din0.ready = dout0.valid && dout0.ready;
    assign din1.ready = din0.valid && din0.ready && (&din0_s.eot);


endmodule
