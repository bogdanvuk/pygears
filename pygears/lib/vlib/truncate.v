module truncate #(
                  parameter NBITS = 0,
                  parameter DIN = 16
                  )
   (
    input logic           clk,
    input                 rst,
    output wire           din_ready,
    input wire            din_valid,
    input wire [DIN-1:0]  din_data,

    input wire            dout_ready,
    output wire           dout_valid,
    output wire [DIN-1:0] dout_data
    );

   assign dout_valid = din_valid;
   assign din_ready = dout_ready;
   assign dout_data = {{din.data[DIN-1:NBITS]}, {(NBITS){1'b0}} };

endmodule
