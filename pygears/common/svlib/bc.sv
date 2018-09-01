
module bc #(
            SIZE = 2
            )
   (
    input logic clk,
    input       rst,
    dti.consumer din,
    dti.producer dout[SIZE-1 : 0]
    );

   logic [SIZE-1 : 0] ready_reg;
   logic [SIZE-1 : 0] ready_all;

   generate
      for (genvar i = 0; i < SIZE; i++) begin
         assign ready_all[i]    = dout[i].ready | ready_reg[i];
         assign dout[i].valid = din.valid & !ready_reg[i];
         assign dout[i].data   = din.data;

         always_ff @(posedge clk) begin
            if (rst) begin
               ready_reg[i] <= 1'b0;
            end
            else begin
               if (din.ready) begin
                  ready_reg[i] <= 1'b0;
               end
               else begin
                  ready_reg[i] <= ready_reg[i] | (dout[i].valid & dout[i].ready);
               end
            end
         end
      end
   endgenerate
   assign din.ready = &ready_all;

endmodule : bc
