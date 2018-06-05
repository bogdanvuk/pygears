module neg #(
             parameter DIN = 0
             )
   (
    input logic clk,
    input       rst,
    dti.consumer din,
    dti.producer dout);


   assign din.ready = dout.ready;

   assign dout.valid = din.valid;
   assign dout.data = -signed'(din.data);

endmodule
