module iceil #(
               DIV = 1
               )
   (
    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout
    );

   wire [$size(din.data)-1:0] din_add = din.data + (DIV - 1);

   assign dout.data = din_add / DIV;

   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
