module rng_hier(
    input clk,
    input rst,
    dti.consumer cfg, // u4 (4)
    dti.producer dout // [u4] (5)

);

      dti #(.W_DATA(6)) ccat_if_s(); // (u1, u4, u1) (6)

      dti #(.W_DATA(1)) const0_if_s(); // u1 (1)

      dti #(.W_DATA(1)) const1_if_s(); // u1 (1)

    ccat ccat_i (
        .clk(clk),
        .rst(rst),
        .din0(const0_if_s),
        .din1(cfg),
        .din2(const1_if_s),
        .dout(ccat_if_s)
    );


    const0 const0_i (
        .clk(clk),
        .rst(rst),
        .dout(const0_if_s)
    );


    const1 const1_i (
        .clk(clk),
        .rst(rst),
        .dout(const1_if_s)
    );


    rng_rng rng_i (
        .clk(clk),
        .rst(rst),
        .cfg(ccat_if_s),
        .dout(dout)
    );



endmodule