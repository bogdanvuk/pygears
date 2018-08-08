module tr_cnt
  (
   input clk,
   input rst,
   dti.consumer din,
   dti.consumer cfg,
   dti.producer dout
   );

   typedef struct packed {
      logic       eot;
      logic [$size(din.data)-2:0] data;
   } din_t;

   typedef struct packed {
      logic [1:0] eot;
      logic [$size(din.data)-2:0] data;
   } dout_t;

   logic [$size(cfg.data)-1:0]    cnt_reg, cnt_next;
   din_t data_in;
   dout_t data_out;
   logic                          handshake;
   logic                          last_data;
   logic                          cnt_done;

   assign handshake = cfg.valid && din.valid && dout.ready;
   assign last_data = (cnt_reg == (cfg.data - 1));
   assign cnt_done = last_data && handshake && data_in.eot;

   assign data_in = din.data;
   assign dout.data = data_out;

   assign data_out.data = data_in.data;
   assign data_out.eot[0] = data_in.eot;
   assign data_out.eot[1] = last_data;

   assign dout.valid = din.valid && cfg.valid;
   assign din.ready  = dout.ready && cfg.valid;

   assign cfg.ready  = cnt_done;

   assign cnt_next = cnt_reg + 1;

   always_ff @(posedge clk) begin
      if (rst || cnt_done) begin
         cnt_reg <= '0;
      end
      else if (handshake && data_in.eot) begin
         cnt_reg <= cnt_next;
      end
   end

endmodule
