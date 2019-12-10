module hsspy
  (
   input rst,
   input clk,
	 dti.consumer din,
	 dti.producer dout,
	 dti.producer spy
   );

   assign dout.valid = din.valid;
   assign din.ready = dout.ready;
   assign dout.data = din.data;

   assign spy.valid = dout.valid && dout.ready;
   assign spy.data = din.data;

endmodule
