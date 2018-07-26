module neq
   (
    input logic clk,
    input       rst,
                dti.consumer din0,
                dti.consumer din1,
                dti.producer dout);

   assign dout.data = din0.data != din1.data;

   logic handshake;

   assign handshake = dout.valid & dout.ready;

   assign din0.ready = handshake;
   assign din1.ready = handshake;

   assign dout.valid = din0.valid & din1.valid;

endmodule
