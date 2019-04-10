module extender #(
                     parameter SIGNED = 0,
                     parameter W_DOUT = 32
                     )
	 (
	  input logic clk,
	  input logic rst,
	  dti.consumer din,
	  dti.producer dout
	  );

   assign dout.valid = din.valid;
   assign din.ready = dout.ready;

   if (SIGNED) begin
      assign dout.data = W_DOUT'(signed'(din.data));
   end else begin
      assign dout.data = W_DOUT'(din.data);
   end

endmodule
