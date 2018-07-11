module max2 #(
             parameter DIN0 = 0,
             parameter DIN1 = 0,
             parameter DIN0_SIGNED = 0,
             parameter DIN1_SIGNED = 0
             )
   (
    input clk,
    input rst,
    dti.consumer din0,
    dti.consumer din1,
    dti.producer dout);

   localparam DOUT = (DIN0 > DIN1) ? DIN1 : DIN0;
   logic max_select;

   if ((!DIN0_SIGNED) && (!DIN1_SIGNED)) begin
      assign max_select = (DOUT'(din0.data) > DOUT'(din1.data));
   end else if ((DIN0_SIGNED) && (!DIN1_SIGNED)) begin
      assign max_select = (DOUT'(signed'(din0.data)) > DOUT'(din1.data));
   end else if ((!DIN0_SIGNED) && (DIN1_SIGNED)) begin
      assign max_select = (DOUT'(din0.data) > DOUT'(signed'(din1.data)));
   end else if ((DIN0_SIGNED) && (DIN1_SIGNED)) begin
      assign max_select = (DOUT'(signed'(din0.data)) > DOUT'(signed'(din1.data)));
   end

   logic handshake;
   assign dout.data = max_select ? DOUT'(din0.data) : DOUT'(din1.data);

   assign handshake = dout.valid & dout.ready;

   assign din0.ready = handshake;
   assign din1.ready = handshake;

   assign dout.valid = din0.valid & din1.valid;

endmodule
