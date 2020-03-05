module cart(
            input logic clk,
            input logic rst,

            dti.consumer din0, // [u4]^2 (6)
            dti.consumer din1, // [()] (1)
            dti.producer dout // [(u4, ())]^3 (7)

            );

   /*verilator tracing_off*/

   dti #(.W_DATA(6)) cart_sync_dout00_s(); // [u4]^2 (6)

   dti #(.W_DATA(1)) cart_sync_dout10_s(); // [()] (1)

   cart_cart_sync cart_sync (
                             .clk(clk),
                             .rst(rst),
                             .din0(din0),
                             .din1(din1),
                             .dout0(cart_sync_dout00_s),
                             .dout1(cart_sync_dout10_s)
                             );


   cart_cart_cat cart_cat (
                           .clk(clk),
                           .rst(rst),
                           .din0(cart_sync_dout00_s),
                           .din1(cart_sync_dout10_s),
                           .dout(dout)
                           );



endmodule
