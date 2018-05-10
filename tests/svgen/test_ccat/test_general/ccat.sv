
module ccat
  (
   input clk,
   input rst,
   dti.consumer din0, // [u4]^5 (9)
   dti.consumer din1, // u1 (1)
   dti.consumer din2, // [u3]^3 (6)
   dti.consumer din3, // [()] (1)
   dti.producer dout // ([u4]^5, u1, [u3]^3, [()]) (17)

   );

   logic all_valid;
   logic handshake;
   assign all_valid = din0.valid && din1.valid && din2.valid && din3.valid;
   assign handshake = dout.valid & dout.ready;

   assign dout.valid = all_valid;
   assign dout.data = { din3.data, din2.data, din1.data, din0.data };

   assign din0.ready = handshake;
   assign din1.ready = handshake;
   assign din2.ready = handshake;
   assign din3.ready = handshake;


endmodule
