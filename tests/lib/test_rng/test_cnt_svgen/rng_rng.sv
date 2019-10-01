module rng_rng(
               input clk,
               input rst,
               dti.consumer cfg, // (u1, u4, u1) (6)
               dti.producer dout // [u4] (5)

               );

   rng #(
         .W_START(1'd1),
         .W_CNT(3'd4),
         .W_INCR(1'd1)
         )
   sv_rng (
             .clk(clk),
             .rst(rst),
             .cfg(cfg),
             .dout(dout)
             );



endmodule
