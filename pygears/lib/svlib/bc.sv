
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

   initial begin
      ready_reg = 0;
   end

   generate
      for (genvar i = 0; i < 32'(SIZE); i++) begin
         assign ready_all[i]    = dout[i].ready | ready_reg[i];
         assign dout[i].valid = din.valid & !ready_reg[i];
         assign dout[i].data   = din.data;

         always @(posedge clk) begin
            if (rst || (!din.valid) || din.ready) begin
               ready_reg[i] <= 1'b0;
            end else if (dout[i].ready) begin
               ready_reg[i] <= 1'b1;
            end
         end
      end
   endgenerate
   assign din.ready = &ready_all;

endmodule : bc
