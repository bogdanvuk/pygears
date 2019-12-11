module rng_hier(
                input logic clk,
                input logic rst,
                dti.consumer cfg, // (u4, u2, u2) (8)
                dti.producer dout // [u4] (5)

                );

   rng #(
         .W_START(3'd4),
         .W_CNT(2'd2),
         .W_INCR(2'd2)
         )
   sv_rng (
             .clk(clk),
             .rst(rst),
             .cfg(cfg),
             .dout(dout)
             );



endmodule
