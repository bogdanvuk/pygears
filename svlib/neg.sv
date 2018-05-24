module neg #(
             parameter TDIN = 0
             )
   (
    input logic clk,
    input       rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout);


   assign din.dready = dout.dready;
   assign dout.eot = 0;

   assign dout.dvalid = din.dvalid;
   assign dout.data = -signed'(din.data);

endmodule
