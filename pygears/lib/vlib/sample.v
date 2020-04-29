module sample #(
                DIN = 0,
                HOLD = 1,
                LATENCY = 0,
                INIT = 0,
                INIT_VALID = 0
                )
  (
   input                 rst,
   input                 clk,
   output wire           din_ready,
   input wire            din_valid,
   input wire [DIN-1:0]  din_data,

   input wire            dout_ready,
   output wire           dout_valid,
   output wire [DIN-1:0] dout_data
   );

   logic [$size(din_data)-1 : 0] din_reg;
   logic                         din_reg_valid;
   logic                         consuming;
   logic                         handshake;

   initial begin
      din_reg_valid = 0;
   end

   always @(posedge clk) begin
      if (rst) begin
         din_reg_valid <= INIT_VALID;
         if (INIT_VALID)
           din_reg <= INIT;

      end else if (handshake || !consuming) begin
         if (din_valid || (HOLD == 0)) begin
            din_reg_valid <= din_valid;
            din_reg <= din_data;
         end
      end
   end

   always @(posedge clk) begin
      if (rst || handshake) begin
         consuming <= 0;
      end else if (dout_valid) begin
         consuming <= 1;
      end
   end

   assign handshake = dout_ready && dout_valid;

   if (LATENCY == 0) begin
      assign dout_data = (!consuming) && (din_valid || (HOLD == 0)) ? din_data : din_reg;
      assign dout_valid = (!consuming) && (din_valid || (HOLD == 0)) ? din_valid : din_reg_valid;
   end else begin
      assign dout_data = din_reg;
      assign dout_valid = din_reg_valid;
   end

   assign din_ready = 1'b1;

endmodule
