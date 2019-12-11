module sieve_7v4
  (
   input logic clk,
   input logic rst,
   dti.consumer din,
   dti.producer dout

   );

   assign dout.data = {din.data[7:4]};

   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
