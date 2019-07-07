module valve
  (
   input clk,
   input rst,
   dti.consumer din, // data_type | Unit
   dti.producer dout //data_type
   );

   typedef struct packed {
      logic       ctrl;
      logic [$size(din.data)-2:0] data;
   } din_t;

   din_t din_s;
   assign din_s = din.data;

   assign dout.valid = din.valid && !din_s.ctrl;
   assign dout.data   = din_s.data;

   assign din.ready = dout.ready | (din_s.ctrl & din.valid);

endmodule
