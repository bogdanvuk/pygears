module fix
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input logic clk,
    input logic rst,

	  dti.consumer din,
	  dti.producer dout
    );

   assign din.ready = dout.ready;
   assign dout.valid = din.valid;

   if (TOUT > 0)
     assign dout.data = TOUT'(VAL);

endmodule
