module reverse
  (
   input logic clk,
   input logic rst,
   dti.consumer din,
   dti.producer dout
   );

   assign dout.data   = {<<{din.data}};
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
