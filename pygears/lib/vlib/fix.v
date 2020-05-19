module fix
  #(
    parameter DIN = 0,
    parameter TOUT = 0,
    parameter VAL = 0
    )
   (
    input                  clk,
    input                  rst,

    output wire            din_ready,
    input wire             din_valid,
    input wire [DIN-1:0]   din_data,

    input wire             dout_ready,
    output wire            dout_valid,
    output wire [TOUT-1:0] dout_data
    );

   assign din_ready = dout_ready;
   assign dout_valid = din_valid;

   if (TOUT > 0)
     assign dout_data = VAL;
   else
     assign dout_data = 0;

endmodule
