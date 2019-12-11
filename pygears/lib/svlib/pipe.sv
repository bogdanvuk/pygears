(*dependency="dreg"*)
module pipe #(parameter LENGTH = 2,
              parameter DIN = 16)
   (
    input logic clk,
    input logic rst,
    dti.consumer din,
    dti.producer dout
    );

   dti#(.W_DATA(DIN)) reg_dout[LENGTH-1:0]();

   generate
      for (genvar i = 0; i < LENGTH; i++) begin
         if (i == 0) begin
            dreg dreg_i (
                         .clk(clk),
                         .rst(rst),
                         .din(din),
                         .dout(reg_dout[i])
                         );
         end else begin
            dreg dreg_i (
                         .clk(clk),
                         .rst(rst),
                         .din(reg_dout[i-1]),
                         .dout(reg_dout[i])
                         );
         end
      end
   endgenerate

   assign dout.data = reg_dout[LENGTH-1].data;
   assign dout.valid = reg_dout[LENGTH-1].valid;
   assign reg_dout[LENGTH-1].ready = dout.ready;

   if (LENGTH == 0) begin
      assign dout.data = din.data;
      assign dout.valid = din.valid;
      assign din.ready = dout.ready;
   end

endmodule
