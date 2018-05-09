module rng_cnt_only_rng(
    input clk,
    input rst,
    dti.consumer cfg, // (u1, u4, u1) (6)
    dti.producer dout // [u4] (5)

);

    rng #(
                .W_START(1),
                .W_CNT(4),
                .W_INCR(1)
    )
     sv_rng_i (
        .clk(clk),
        .rst(rst),
        .cfg(cfg),
        .dout(dout)
    );



endmodule