module rng_hier(
    input clk,
    input rst,
    dti.consumer cfg, // (u4, u2, u2) (8)
    dti.producer dout // [u4] (5)

);

    rng #(
                .W_START(4),
                .W_CNT(2),
                .W_INCR(2)
    )
     sv_rng_i (
        .clk(clk),
        .rst(rst),
        .cfg(cfg),
        .dout(dout)
    );



endmodule