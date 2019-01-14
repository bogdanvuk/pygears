module qtake
  (
   input clk,
   input rst,
   dti.consumer cfg,
   dti.consumer din,
   dti.producer dout
   );

   typedef struct packed
                  {
                     logic [1:0] eot;
                     logic [$size(din.data)-3:0] data;
                  } din_t;

   din_t din_s;
   din_t dout_s;
   logic [$size(cfg.data)-1:0]                   cnt_reg, cnt_next;
   logic                                         handshake;
   logic                                         cnt_done_reg, cnt_done_next;

   assign din_s = din.data;
   assign in_handshake = din.valid & din.ready;
   assign tr_done = in_handshake & cfg.valid & din_s.eot[1] & din_s.eot[0];
   assign handshake = dout.ready & cfg.valid & din.valid & din_s.eot[0]; // shake on eot

   assign cnt_done_next = cnt_done_reg & (cnt_next != cfg.data);
   assign cnt_next = cnt_reg + 1;

   always_ff @(posedge clk) begin
     if(rst | tr_done) begin
        cnt_reg <= 0;
        cnt_done_reg <= 1'b1;
     end else if (handshake & cnt_done_reg) begin
        cnt_reg <= cnt_next;
        cnt_done_reg <= cnt_done_next;
     end
   end

   assign dout_s.data = din_s.data;
   assign dout_s.eot[0] = din_s.eot[0];
   assign dout_s.eot[1] = din_s.eot[1] || (!cnt_done_next);

   assign dout.data = dout_s;
   assign dout.valid = cfg.valid & din.valid & cnt_done_reg;

   assign din.ready = cnt_done_reg ? (dout.ready & cfg.valid) : cfg.valid;

   assign cfg.ready = tr_done;

endmodule
