module sustain
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input logic clk,
    input logic rst,

	  dti.producer dout
    );

   assign dout.valid = 1'b1;
   if (TOUT > 0)
     assign dout.data = TOUT'(VAL);

endmodule
