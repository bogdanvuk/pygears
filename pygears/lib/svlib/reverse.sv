module reverse
  (
   input clk,
   input rst,
   dti.consumer din,
   dti.producer dout
   );

   assign dout.data   = {<<{din.data}};
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
