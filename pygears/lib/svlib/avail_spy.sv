module avail_spy
  (
   input logic rst,
   input logic clk,
	 dti.consumer din,
	 dti.producer dout0,
	 dti.producer dout1
   );
   assign dout0.valid = 1;
   assign din.ready = 1;
   assign dout0.data = din.valid;

   assign dout1.valid = din.valid;
   assign dout1.data = din.data;
   assign din.ready = dout1.ready;

endmodule
