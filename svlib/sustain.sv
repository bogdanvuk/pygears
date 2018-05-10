module sustain
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input clk,
    input rst,

	dti_s_if.producer dout
    );

   assign dout.dvalid = 1'b1;
   assign dout.data = TOUT'(VAL);
   assign dout.eot = 1'b0;

endmodule
