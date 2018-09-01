module mod #(
             parameter DIN0_SIGNED = 0,
             parameter DIN1_SIGNED = 0
             )
   (
    input logic clk,
    input       rst,
                dti.consumer din0,
                dti.consumer din1,
                dti.producer dout);

   if ((!DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = din0.data % din1.data;
   end else if ((DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = signed'(din0.data) % din1.data;
   end else if ((!DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = din0.data % signed'(din1.data);
   end else if ((DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = signed'(din0.data) % signed'(din1.data);
   end

   logic handshake;

   assign handshake = dout.valid & dout.ready;

   assign din0.ready = handshake;
   assign din1.ready = handshake;

   assign dout.valid = din0.valid & din1.valid;

endmodule
