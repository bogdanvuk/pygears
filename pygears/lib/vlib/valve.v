module valve #(
                  parameter DIN = 0
                  )
  (
   input                 clk,
   input                 rst,

   output wire           cond_ready,
   input wire            cond_valid,
   input wire [0:0]      cond_data,

   output wire           din_ready,
   input wire            din_valid,
   input wire [DIN-1:0]  din_data,

   input wire            dout_ready,
   output wire           dout_valid,
   output wire [DIN-1:0] dout_data
   );

   assign dout_valid = cond_valid && (cond_data ? din_valid : 0);
   assign din_ready = cond_valid ? dout_ready : 0;
   assign cond_ready = dout_valid ? dout_ready : 1'b1;

   assign dout_data = din_data;

endmodule
