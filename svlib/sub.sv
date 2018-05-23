module sub #(
             parameter TDIN0 = 0,
             parameter TDIN1 = 0,
             parameter DIN0_SIGNED = 0,
             parameter DIN1_SIGNED = 0
             )
   (
    input logic clk,
    input       rst,
    dti_s_if.consumer din0,
    dti_s_if.consumer din1,
    dti_s_if.producer dout);

   localparam TDOUT = (TDIN0 > TDIN1) ? TDIN0 : TDIN1 + 1;

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
   assign handshake = dout.dvalid & dout.dready;

   assign din0.dready = handshake;
   assign din1.dready = handshake;
   assign dout.eot = 0;

   assign dout.dvalid = din0.dvalid & din1.dvalid;

endmodule
