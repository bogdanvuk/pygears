module sustain
  #(
    parameter DOUT = 0,
    parameter VAL = 0
    )
   (
    input                  clk,
    input                  rst,

    input wire             dout_ready,
    output wire            dout_valid,
    output wire [DOUT-1:0] dout_data
    );

   assign dout_valid = 1'b1;
   assign dout_data = VAL;

endmodule
