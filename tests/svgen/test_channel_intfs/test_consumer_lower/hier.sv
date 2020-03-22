module hier(
    input logic clk,
    input logic rst,
    dti.consumer din, // u2 (2)
    dti.consumer channeled, // u1 (1)
    dti.producer dout // (u2, u1) (3)

);

    hier_func func (
        .clk(clk),
        .rst(rst),
        .din(din),
        .channeled(channeled),
        .dout(dout)
    );



endmodule
