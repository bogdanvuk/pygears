module reverse
  (
   input                clk,
   input                rst,
   output wire          din_ready,
   input wire           din_valid,
   input wire [DIN-1:0] din_data,

   input wire           dout_ready,
   output wire          dout_valid,
   output reg [DIN-1:0] dout_data
   );

   integer     ii;

   always @*
     begin
        for (ii=wi; ii >= 0; ii=ii-1)
          dout_data[wi-ii]=din_data[ii];
     end

   assign dout_valid = din_valid;
   assign din_ready  = dout_ready;

endmodule
