module sustain
  #(
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input                  clk,
    input                  rst,

    input wire             dout_ready,
    output wire            dout_valid,
    output wire [TOUT-1:0] dout_data
    );

   assign dout_valid = 1'b1;
   assign dout_data = VAL;

endmodule
