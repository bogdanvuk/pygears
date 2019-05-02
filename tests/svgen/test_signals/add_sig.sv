module add_sig
   (
    output [15:0] din_sig,
	                dti.consumer din,
	                dti.producer dout
    );

   assign dout.data = din.data + din_sig;

   assign dout.valid = din.valid;
   assign din.ready = dout.ready;

endmodule
