module trigreg  #(
                   LATENCY = 1,
                   DIN = 0
                   )
  (
   input logic rst,
   input logic clk,
	 dti.consumer din,
	 dti.producer dout
   );

   typedef struct packed {
      logic [0:0]  valid;
      logic [DIN-2:0] data;
   } din_t;

   dti #(.W_DATA(DIN-1)) sample_din();

   din_t din_s;
   logic [$size(din.data)-2:0] din_data_reg;
   logic din_valid_reg;

   assign din_s = din.data;
   assign din.ready = 1;

   always @(posedge clk) begin

      if (rst) begin
         din_valid_reg <= 0;
      end else begin
         if (din.valid) begin
            din_valid_reg <= din_s.valid;
            din_data_reg <= din_s.data;
         end
      end
   end

   assign sample_din.data = din_data_reg;
   assign sample_din.valid = din_valid_reg;

   sample #(.LATENCY(LATENCY-1), .HOLD(0))
   sample_i (
             .clk(clk),
             .rst(rst),
             .din(sample_din),
             .dout(dout)
             );

endmodule
