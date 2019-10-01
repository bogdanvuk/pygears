module hier(
    input clk,
    input rst,
    dti.consumer top_din1, // u1 (1)
    dti.consumer top_din2, // u2 (2)
    dti.producer top_ret1, // u2 (2)
    dti.producer top_ret2 // u2 (2)

);

      dti #(.W_DATA(2)) ret1(); // u2 (2)
      dti #(.W_DATA(2)) ret1_bc[1:0](); // u2 (2)
    bc #(
                .SIZE(2'd2)
    )
     bc_ret1 (
        .clk(clk),
        .rst(rst),
        .din(ret1),
        .dout(ret1_bc)
    );

    assign top_ret1.valid = ret1_bc[1].valid;
    assign top_ret1.data = ret1_bc[1].data;
    assign ret1_bc[1].ready = top_ret1.ready;

      dti #(.W_DATA(2)) top_din2_bc[1:0](); // u2 (2)
    bc #(
                .SIZE(2'd2)
    )
     bc_top_din2 (
        .clk(clk),
        .rst(rst),
        .din(top_din2),
        .dout(top_din2_bc)
    );


    fgear fgear0 (
        .clk(clk),
        .rst(rst),
        .arg1(top_din1),
        .arg2(top_din2_bc[0]),
        .ret(ret1)
    );


    fgear fgear1 (
        .clk(clk),
        .rst(rst),
        .arg1(ret1_bc[0]),
        .arg2(top_din2_bc[1]),
        .ret(top_ret2)
    );



endmodule
