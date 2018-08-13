module local_rst
  (
   input  clk,
   input  rst,
   output local_rst,
   dti.consumer din
   );

   assign din.ready = 1;
   assign local_rst = din.valid || rst;

endmodule
