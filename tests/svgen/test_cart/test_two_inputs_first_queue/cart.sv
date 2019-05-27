module cart(
    input clk,
    input rst,

    dti.consumer din0, // [u4] (5)
    dti.consumer din1, // u1 (1)
    dti.producer dout // [(u4, u1)] (6)

);

/*verilator tracing_off*/

      dti #(.W_DATA(5)) cart_sync_dout0(); // [u4] (5)

      dti #(.W_DATA(1)) cart_sync_dout1(); // u1 (1)

    cart_cart_sync cart_sync (
        .clk(clk),
        .rst(rst),
        .din0(din0),
        .din1(din1),
        .dout0(cart_sync_dout0),
        .dout1(cart_sync_dout1)
    );


    cart_cart_cat cart_cat (
        .clk(clk),
        .rst(rst),
        .din0(cart_sync_dout0),
        .din1(cart_sync_dout1),
        .dout(dout)
    );



endmodule