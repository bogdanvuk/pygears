module data_dly #(parameter LEN = 5,
                  parameter W_DIN = 16)
   (
    input logic clk,
    input logic rst,
    dti.consumer din,
    dti.producer dout
    );

   logic dly_done;
   logic [LEN-1:0] reg_valid;
   dti#(.W_DATA(W_DIN)) reg_dout[LEN-1:0]();
   initial begin
      dly_done = 0;
   end

   always @(posedge clk) begin
      if (rst || !(|reg_valid)) begin
         dly_done = 0;
      end else begin
         if (&reg_valid) begin
            dly_done = 1;
         end
      end
   end

   generate
      for (genvar i = 0; i < LEN; i++) begin
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
         assign reg_valid[i] = reg_dout[i].valid;
      end
   endgenerate


   assign dout.data = reg_dout[LEN-1].data;
   assign dout.valid = reg_dout[LEN-1].valid && dly_done;
   assign reg_dout[LEN-1].ready = dout.ready && dly_done;

endmodule
