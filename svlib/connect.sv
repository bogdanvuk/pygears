module connect
   (
    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout
    );

   assign din.ready = dout.ready;
   assign dout.data = din.data;
   assign dout.valid = din.valid;

endmodule
