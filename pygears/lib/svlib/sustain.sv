module sustain
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input clk,
    input rst,

	  dti.producer dout
    );

   assign dout.valid = 1'b1;
   assign dout.data = TOUT'(VAL);

endmodule
