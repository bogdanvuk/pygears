
module ccat
(
    input clk,
    input rst,
    dti.consumer din0, // u1 (1)
    dti.consumer din1, // u4 (4)
    dti.consumer din2, // u1 (1)
    dti.producer dout // (u1, u4, u1) (6)

);

    logic  all_valid;
    logic  handshake;
    assign all_valid = din0.valid && din1.valid && din2.valid;
    assign handshake = dout.valid & dout.ready;

    assign dout.valid = all_valid;
    assign dout.data = { din2.data, din1.data, din0.data };

    assign din0.ready = handshake;
    assign din1.ready = handshake;
    assign din2.ready = handshake;


endmodule