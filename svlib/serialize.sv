module serialize # (
                    parameter DIN = 0,
                    parameter DOUT = 0
                    )
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   // ---------------------------------------------------------------------------
   // internal signals
   // ---------------------------------------------------------------------------

   localparam DIN_SIZE = DIN / DOUT;

   logic [$clog2(DIN_SIZE)-1 : 0] count_s;
   logic [DOUT-1 : 0] splitted_input[DIN_SIZE-1 : 0];

   logic last_data_s;
   assign last_data_s = (count_s == (DIN/DOUT-1));

   // ---------------------------------------------------------------------------
   // interfaces
   // ---------------------------------------------------------------------------

   generate
      for (genvar i = 0; i < DIN/DOUT; i++) begin
         assign splitted_input[i] = din.data[((i+1)*DOUT)-1 : (i*DOUT)];
      end
   endgenerate

   assign dout.valid = din.valid;
   assign dout.data   = splitted_input[count_s];
   assign din.ready  = dout.ready & last_data_s;

   // ---------------------------------------------------------------------------
   // counter
   // ---------------------------------------------------------------------------

   always_ff @(posedge clk) begin
      if (rst) begin
         count_s <= '0;
      end
      else begin
         if (dout.ready & din.valid) begin
            if (last_data_s) begin
               count_s <= '0;
            end
            else begin
               count_s <= count_s + 1;
            end
         end
      end
   end

endmodule
