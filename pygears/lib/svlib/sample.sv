module sample #(
                HOLD = 1,
                LATENCY = 0,
                INIT = 0,
                INIT_VALID = 0
                )
  (
   input rst,
   input clk,
	 dti.consumer din,
	 dti.producer dout
   );

   logic [$size(din.data)-1 : 0] din_reg;
   logic                         din_reg_valid;
   logic                         consuming;
   logic                         handshake;

   initial begin
      din_reg_valid = 0;
   end

   always @(posedge clk) begin
      din_reg <= din_reg;
      din_reg_valid <= ((HOLD == 1) && din_reg_valid) || din.valid;

      consuming <= 0;

      if (rst) begin
         din_reg <= 0;

         din_reg_valid <= INIT_VALID;
         if (INIT_VALID)
           din_reg <= INIT;

      end else if (handshake || !din_reg_valid) begin
         if (din.valid || (HOLD == 0)) begin
            din_reg <= din.data;
         end
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
   end

   assign dout.valid = din_reg_valid;

   assign din.ready = 1'b1;

endmodule
