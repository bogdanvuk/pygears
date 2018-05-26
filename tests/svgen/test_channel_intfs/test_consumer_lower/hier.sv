module hier(
    input clk,
    input rst,
    dti.consumer din, // u2 (2)
    dti.consumer channeled, // u1 (1)
    dti.producer dout // (u2, u1) (3)

);

    func func_i (
        .clk(clk),
        .rst(rst),
        .din(din),
        .channeled(channeled),
        .dout(dout)
    );



endmodule