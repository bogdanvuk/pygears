module sustain_ping
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input clk,
    input rst,

	  dti.consumer ping,
	  dti.producer dout
    );

   assign ping.ready = dout.ready;
   assign dout.valid = ping.valid;
   assign dout.data = TOUT'(VAL);

endmodule
