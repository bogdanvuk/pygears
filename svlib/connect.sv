module connect
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   assign din.ready = dout.ready;
   assign dout.data = din.data;
   assign dout.valid = din.valid;

endmodule
