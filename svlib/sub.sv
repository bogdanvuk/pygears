module sub #(
             parameter DIN0 = 0,
             parameter DIN1 = 0,
             parameter DIN0_SIGNED = 0,
             parameter DIN1_SIGNED = 0
             )
   (
    input logic clk,
    input       rst,
    dti.consumer din0,
    dti.consumer din1,
    dti.producer dout);

   localparam TDOUT = (DIN0 > DIN1) ? (DIN0 + 1) : (DIN1 + 1);

   if ((!DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = TDOUT'(din0.data) - TDOUT'(din1.data);
   end else if ((DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = TDOUT'(signed'(din0.data)) - TDOUT'(din1.data);
   end else if ((!DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = TDOUT'(din0.data) - TDOUT'(signed'(din1.data));
   end else if ((DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = TDOUT'(signed'(din0.data)) - TDOUT'(signed'(din1.data));
   end

   logic                 handshake;
   assign handshake = dout.valid & dout.ready;

   assign din0.ready = handshake;
   assign din1.ready = handshake;

   assign dout.valid = din0.valid & din1.valid;

endmodule
