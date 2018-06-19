module serialize (
                  input clk,
                  input rst,
                  dti.consumer din,
                  dti.producer dout
                  );

   // ---------------------------------------------------------------------------
   // internal signals
   // ---------------------------------------------------------------------------

   logic [$clog2($size(din.data)/$size(dout.data))-1 : 0] count_s;
   logic [$size(din.data)/$size(dout.data)-1 : 0] [$size(dout.data)-1 : 0] splitted_input;

   logic                                                                   last_data_s;
   assign last_data_s = (count_s == ($size(din.data)/$size(dout.data)-1));

   // ---------------------------------------------------------------------------
   // interfaces
   // ---------------------------------------------------------------------------

   generate
      for (genvar i = 0; i < $size(din.data)/$size(dout.data); i++) begin
         assign splitted_input[i] = din.data[((i+1)*$size(dout.data))-1 : (i*$size(dout.data))];
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
      end else begin
         if (dout.ready & din.valid) begin
            if (last_data_s) begin
               count_s <= '0;
            end else begin
               count_s <= count_s + 1;
            end
         end
      end
   end

endmodule
