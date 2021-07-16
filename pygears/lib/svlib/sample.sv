module sample #(
                HOLD = 1,
                LATENCY = 0,
                INIT = 0,
                INIT_VALID = 0
                )
  (
   input logic rst,
   input logic clk,
	 dti.consumer din,
	 dti.producer dout
   );

   logic [$size(din.data)-1 : 0] din_reg;
   logic                         din_reg_valid;
   logic                         consuming;
   logic                         handshake;

   initial begin
      din_reg_valid = INIT_VALID;
      consuming = 0;
      if (INIT_VALID)
        din_reg = INIT;
   end

   always @(posedge clk) begin
      if (rst) begin
         din_reg_valid <= INIT_VALID;
         if (INIT_VALID)
           din_reg <= INIT;

      end else if (handshake || !consuming) begin
         if (din.valid || (HOLD == 0)) begin
            din_reg_valid <= din.valid;
            din_reg <= din.data;
         end
      end
   end

   always @(posedge clk) begin
      if (rst || handshake) begin
         consuming <= 0;
      end else if (dout.valid) begin
         consuming <= 1;
      end
   end

   assign handshake = dout.ready && dout.valid;

   if (LATENCY == 0) begin
      assign dout.data = (!consuming) && (din.valid || (HOLD == 0)) ? din.data : din_reg;
      assign dout.valid = (!consuming) && (din.valid || (HOLD == 0)) ? din.valid : din_reg_valid;
   end else begin
      assign dout.data = din_reg;
      assign dout.valid = din_reg_valid;
   end

   assign din.ready = 1'b1;

endmodule
