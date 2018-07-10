// Clip
// clips the input transaction into two separate transactions by
// sending eot after a given number of data has passed (specified by
// configuration). The second eot is passed from input.

// Implementation notes:
// - input eot can be skipped if it comes to soon (before cfg.data number of data)

module clip #(
              CLIP_STOP = 0
              )
   (
    input clk,
    input rst,
    dti.consumer cfg,
    dti.consumer din,
    dti.producer dout
    );

   typedef struct packed
                  {
                     logic eot;
                     logic [$size(din.data)-2:0] data;
                  } din_t;

   din_t din_s;
   din_t dout_s;
   logic [$size(cfg.data)-1:0] cnt_reg, cnt_next;
   logic                       pass_eot_reg, pass_eot_next;
   logic                       eot_internal_cond;
   logic                       clip_eot_cond;
   logic                       eot;
   logic                       handshake;

   assign din_s = din.data;

   assign eot_internal_cond = din_s.eot & din.valid |
                              ((CLIP_STOP == 1) & (clip_eot_cond & cfg.valid & din.valid));
   assign clip_eot_cond = (cnt_next == cfg.data) & !pass_eot_reg;

   assign eot = eot_internal_cond & cfg.valid;

   assign handshake = dout.ready & cfg.valid & din.valid;

   assign dout_s.data = din.data;
   assign dout_s.eot = eot | (clip_eot_cond & cfg.valid & din.valid);
   assign dout.data = dout_s;
   assign dout.valid = cfg.valid & din.valid;
   assign din.ready = dout.ready & cfg.valid;
   assign cfg.ready = eot & din.ready;

   assign pass_eot_next = clip_eot_cond | pass_eot_reg;
   assign cnt_next = cnt_reg + (pass_eot_reg ? 0 : 1);

   always_ff @(posedge clk)
     if (rst | (eot & dout.ready)) begin
        pass_eot_reg <= 1'b0;
        cnt_reg <= 0;
     end else if (handshake) begin
        cnt_reg <= cnt_next;
        pass_eot_reg <= pass_eot_next;
     end

endmodule : clip
