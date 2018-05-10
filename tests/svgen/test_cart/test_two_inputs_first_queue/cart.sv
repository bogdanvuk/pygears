
module cart
  (
   input clk,
   input rst,
   dti.consumer din0, // [u4] (5)
   dti.consumer din1, // u1 (1)
   dti.producer dout // [(u4, u1)] (6)

   );
   typedef struct packed { // [u4]
      logic [0:0] eot; // u1
      logic [3:0] data; // u4
   } din0_t;

   typedef struct packed { // u1
      logic [0:0] data; // u1
   } din1_t;

   typedef struct packed { // [(u4, u1)]
      logic [0:0] eot; // u1
      logic [4:0] data; // u5
   } dout_t;


   din0_t din0_s;
   din1_t din1_s;
   dout_t dout_s;

   assign din0_s = din0.data;
   assign din1_s = din1.data;

   assign dout_s.eot = { din0_s.eot };
   assign dout_s.data = { din1_s.data, din0_s.data };

   logic          handshake;
   assign dout.valid = din0.valid & din1.valid;
   assign handshake = dout.valid && dout.ready;
   assign dout.data = dout_s;

   assign din0.ready = handshake && 1;
   assign din1.ready = handshake;



endmodule
