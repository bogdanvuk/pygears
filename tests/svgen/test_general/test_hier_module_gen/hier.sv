module hier(
    input logic clk,
    input logic rst,

    dti.consumer top_din1, // u1 (1)
    dti.consumer top_din2, // u2 (2)
    dti.producer top_ret1, // u2 (2)
    dti.producer top_ret2 // u2 (2)

);

/*verilator tracing_off*/

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


      dti #(.W_DATA(2)) ret10_s(); // u2 (2)
      dti #(.W_DATA(2)) ret10_s_bc[1:0](); // u2 (2)
    bc #(
                .SIZE(2'd2)
    )
     bc_ret10_s (
        .clk(clk),
        .rst(rst),
        .din(ret10_s),
        .dout(ret10_s_bc)
    );

    assign top_ret1.valid = ret10_s_bc[1].valid;
    assign top_ret1.data = ret10_s_bc[1].data;
    assign ret10_s_bc[1].ready = top_ret1.ready;

    hier_fgear0 fgear0 (
        .clk(clk),
        .rst(rst),
        .arg1(top_din1),
        .arg2(top_din2_bc[0]),
        .ret(ret10_s)
    );


    hier_fgear1 fgear1 (
        .clk(clk),
        .rst(rst),
        .arg1(ret10_s_bc[0]),
        .arg2(top_din2_bc[1]),
        .ret(top_ret2)
    );



endmodule
