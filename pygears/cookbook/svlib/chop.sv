module chop
  (
   input clk,
   input rst,
   dti.consumer din,
   dti.consumer cfg,
   dti.producer dout
   );

   typedef struct packed
                  {
                     logic eot;
                     logic [$size(din.data)-2:0] data;
                  } din_t;

   typedef struct packed
                  {
                     logic [1:0] eot;
                     logic [$size(din.data)-2:0] data;
                  } dout_t;

   din_t din_s;
   dout_t dout_s;

   logic [$size(cfg.data)-1:0]                   cnt_reg, cnt_next;
   logic                                         eot_internal_cond;
   logic                                         eot;
   logic                                         handshake;

   assign din_s = din.data;

   assign dout.data = dout_s;

   assign dout.valid = din.valid & cfg.valid;
   assign din.ready = dout.ready & cfg.valid;

   assign handshake = dout.valid & dout.ready;

   assign cfg.ready = din_s.eot & handshake;

   assign cnt_next = cnt_reg + 1;
   assign eot_internal_cond = (cnt_reg == cfg.data - 1) | din_s.eot;
   assign eot = eot_internal_cond & dout.valid;

   assign dout_s.data = din_s.data;
   assign dout_s.eot[0] = eot_internal_cond;
   assign dout_s.eot[1] = din_s.eot;

   always_ff @(posedge clk) begin
      if(rst | (eot & dout.ready)) begin
         cnt_reg <= 0;
      end else if (handshake) begin
         cnt_reg <= cnt_next;
      end
   end

endmodule
