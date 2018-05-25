module neg #(
             parameter DIN = 0
             )
   (
    input logic clk,
    input       rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout);


   assign din.ready = dout.ready;
   assign dout.eot = 0;

   assign dout.valid = din.valid;
   assign dout.data = -signed'(din.data);

endmodule
