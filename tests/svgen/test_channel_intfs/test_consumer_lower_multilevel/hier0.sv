module hier0(
    input clk,
    input rst,
    dti.consumer din, // u2 (2)
    dti.consumer channeled, // u1 (1)
    dti.producer dout0, // (u2, u1) (3)
    dti.producer dout1, // (u2, u1) (3)
    dti.producer dout2 // (u2, u1) (3)

);

      dti #(.W_DATA(2)) din_bc[2:0](); // u2 (2)
    bc #(
                .SIZE(2'd3)
    )
     bc_din (
        .clk(clk),
        .rst(rst),
        .din(din),
        .dout(din_bc)
    );


      dti #(.W_DATA(1)) channeled_bc[2:0](); // u1 (1)
    bc #(
                .SIZE(2'd3)
    )
     bc_channeled (
        .clk(clk),
        .rst(rst),
        .din(channeled),
        .dout(channeled_bc)
    );


    func func0 (
        .clk(clk),
        .rst(rst),
        .din(din_bc[0]),
        .channeled(channeled_bc[0]),
        .dout(dout0)
    );


    func func1 (
        .clk(clk),
        .rst(rst),
        .din(din_bc[1]),
        .channeled(channeled_bc[1]),
        .dout(dout1)
    );


    hier0_hier1 hier1 (
        .clk(clk),
        .rst(rst),
        .din(din_bc[2]),
        .channeled(channeled_bc[2]),
        .dout(dout2)
    );



endmodule
