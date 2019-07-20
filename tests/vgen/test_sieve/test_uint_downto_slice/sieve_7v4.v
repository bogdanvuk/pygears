module sieve_7v4
  (
   input             clk,
   input             rst,
   output wire       din_ready,
   input wire        din_valid,
   input wire [7:0]  din_data,
   input wire        dout_ready,
   output wire       dout_valid,
   output wire [3:0] dout_data

   );

   assign dout_data = {din_data[7:4]};

   assign dout_valid = din_valid;
   assign din_ready  = dout_ready;

endmodule
