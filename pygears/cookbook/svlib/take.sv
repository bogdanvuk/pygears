module take #(
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
   logic [$size(cfg.data)-1:0]                   cnt_reg, cnt_next;
   logic                                         handshake;
   logic                                         eot_internal_cond;
   logic                                         eot;
   logic                                         pass_in_eot_reg, pass_in_eot_next;

   assign cnt_next = cnt_reg + 1;
   assign pass_in_eot_next = pass_in_eot_reg & (cnt_next !=cfg.data);
   assign din_s = din.data;

   always_ff @(posedge clk)
     if(rst | (din_s.eot & handshake)) begin
        cnt_reg <= 0;
        pass_in_eot_reg <= 1'b1;
     end else if (handshake & pass_in_eot_reg) begin
        cnt_reg <= cnt_next;
        pass_in_eot_reg <= pass_in_eot_next;
     end

   assign eot_internal_cond = (cnt_next == cfg.data) | (din_s.eot & pass_in_eot_reg);
   assign handshake = din.ready & cfg.valid & din.valid;
   assign eot = eot_internal_cond & din.valid & cfg.valid;

   assign dout_s.data = din_s.data;
   assign dout_s.eot = eot;
   assign dout.data = dout_s;
   // assign dout.eot = 0;
   assign dout.valid = cfg.valid & din.valid & pass_in_eot_reg;
   assign din.ready = cfg.valid & (dout.ready || !pass_in_eot_reg);
   assign cfg.ready = din_s.eot & din.valid & dout.ready;

endmodule : take
