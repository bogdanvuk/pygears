module release_after_eot
  #(
    parameter W_DIN = 16,
    parameter W_PRED = 16
    )
   (
    input logic clk,
    input logic rst,
    dti.consumer din,
    dti.consumer pred,
    dti.producer dout,
    dti.producer pred_out
    );

   typedef struct packed {
      logic       eot;
      logic [W_PRED-2:0] data;
   } pred_t;

   pred_t pred_s;
   logic release_reg;
   logic handshake;

   assign pred_s = pred.data;

   assign pred.ready     = pred_out.ready;
   assign pred_out.data   = pred.data;
   assign pred_out.valid = pred.valid;

   assign handshake = pred.valid && pred_s.eot;

     always @(posedge clk) begin
        if(rst) begin
           release_reg <= 0;
        end else if (handshake) begin
           release_reg <= 1;
        end
     end

   assign dout.data   = din.data;
   assign dout.valid = din.valid && release_reg;
   assign din.ready  = dout.ready && release_reg;

endmodule
