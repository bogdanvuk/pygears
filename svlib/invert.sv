module invert
   (
    input logic clk,
    input       rst,
                dti.consumer din,
                dti.producer dout);

   assign dout.data = ~din.data;

   logic handshake;

   assign handshake = dout.valid & dout.ready;

   assign din.ready = handshake;

   assign dout.valid = din.valid;

endmodule
