module mul #(
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

   localparam TDOUT = TDIN0 + TDIN1;

   if ((!DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = din0.data * din1.data;
   end else if ((DIN0_SIGNED) && (!DIN1_SIGNED)) begin
       assign dout.data = signed'(din0.data) * din1.data;
   end else if ((!DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = din0.data * signed'(din1.data);
   end else if ((DIN0_SIGNED) && (DIN1_SIGNED)) begin
       assign dout.data = signed'(din0.data) * signed'(din1.data);
   end

   logic handshake;

   assign handshake = dout.dvalid & dout.dready;

   assign din0.dready = handshake;
   assign din1.dready = handshake;
   assign dout.eot = 0;

   assign dout.dvalid = din0.dvalid & din1.dvalid;

endmodule
