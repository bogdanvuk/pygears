
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
    assign din0.ready = dout0.ready;
    assign dout1.valid = all_valid;
    assign dout1.data = din1.data;
    assign din1.ready = dout1.ready;


endmodule
