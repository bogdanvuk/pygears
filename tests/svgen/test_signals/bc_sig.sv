module bc_sig
   (
    output [15:0] dout_sig,
	         dti.consumer din,
	         dti.producer dout
    );

   assign dout_sig = din.data;
   assign dout.data = din.data;

   assign dout.valid = din.valid;
   assign din.ready = dout.ready;

endmodule
