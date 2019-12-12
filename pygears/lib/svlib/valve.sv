module valve
  (
   input logic clk,
   input logic rst,

   dti.consumer cond,
   dti.consumer din,
   dti.producer dout
   );

   assign dout.valid = cond.valid && (cond.data ? din.valid : 0);
   assign din.ready = cond.valid ? dout.ready : 0;
   assign cond.ready = dout.valid ? dout.ready : 1'b1;

   assign dout.data = din.data;

endmodule
