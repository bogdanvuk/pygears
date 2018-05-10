
module zip_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // u4 (4)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // u4 (4)

);

      dti #(.W_DATA(6)) din0_if(); // [u3]^3 (6)
      dti #(.W_DATA(4)) din1_if(); // u4 (4)

    logic all_valid;
    assign all_valid   = din0.valid && din1.valid;

    assign dout0_if.valid = all_valid;
    assign dout0_if.data = din0.data;
    assign din0.ready = dout0_if.dready;
    assign dout1_if.valid = all_valid;
    assign dout1_if.data = din1.data;
    assign din1.ready = dout1_if.dready;


    zip_sync_syncguard syncguard (
        .clk(clk),
        .rst(rst),
        .din0(din0_if),
        .din1(din1_if),
        .dout0(dout0),
        .dout1(dout1)
    );

endmodule