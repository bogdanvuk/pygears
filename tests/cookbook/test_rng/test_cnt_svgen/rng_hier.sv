module rng_hier(
                input clk,
                input rst,
                dti.consumer cfg, // u4 (4)
                dti.producer dout // [u4] (5)

                );

   dti #(.W_DATA(6)) ccat_s(); // (u1, u4, u1) (6)

   dti #(.W_DATA(1)) const0_s(); // u1 (1)

   dti #(.W_DATA(1)) const1_s(); // u1 (1)

   rng_ccat ccat_i (
                    .clk(clk),
                    .rst(rst),
                    .din0(const0_s),
                    .din1(cfg),
                    .din2(const1_s),
                    .dout(ccat_s)
                    );


   sustain #(
             .TOUT(1'd1)
             )
   const0_i (
             .clk(clk),
             .rst(rst),
             .dout(const0_s)
             );


   sustain #(
             .VAL(1'd1),
             .TOUT(1'd1)
             )
   const1_i (
             .clk(clk),
             .rst(rst),
             .dout(const1_s)
             );


   rng_rng rng_i (
                  .clk(clk),
                  .rst(rst),
                  .cfg(ccat_s),
                  .dout(dout)
                  );



endmodule
