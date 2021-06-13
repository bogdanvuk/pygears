module empty
  (
   input logic clk,
   input logic rst,
	 dti.producer dout
   );

   assign dout.valid = 0;
   assign dout.data = 'x;

endmodule
