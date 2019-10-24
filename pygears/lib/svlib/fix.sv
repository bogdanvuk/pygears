module fix
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input clk,
    input rst,

	  dti.consumer din,
	  dti.producer dout
    );

   assign din.ready = dout.ready;
   assign dout.valid = din.valid;
   assign dout.data = TOUT'(VAL);

endmodule
