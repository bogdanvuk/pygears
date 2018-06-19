module replicate
  #(
    parameter W_VAL = 0,
    parameter W_LEN = 0
    )
  (
   input rst,
   input clk,
   dti.consumer din,
   dti.producer dout
   );

   typedef struct packed
                  {
                     logic [W_VAL-1:0] val;
                     logic [W_LEN-1:0] len;
                  } din_t;

   typedef struct packed
                  {
                     logic eot;
                     logic [$size(dout.data)-2:0] data;
                  } dout_t;

   din_t din_s;
   logic [W_LEN-1:0] cnt_reg;
   logic [W_LEN-1:0] cnt_next;
   logic             eot_internal_cond;
   logic             eot;
   logic             handshake;
   logic             eotshake;

   assign din_s = din.data;

   assign cnt_next = cnt_reg + 1;

   always_ff @(posedge clk)
     if (rst | eotshake) begin
        cnt_reg <= 0;
     end else if (handshake) begin
        cnt_reg <= cnt_next;
     end

   assign eot_internal_cond = (cnt_next == din_s.len);
   assign eot = eot_internal_cond & din.valid;
   assign handshake = dout.ready & din.valid;
   assign eotshake = dout.ready & eot;

   dout_t dout_s;
   assign dout_s.data = din_s.val;
   assign dout_s.eot = eot;

   assign dout.data = dout_s;
   assign dout.valid = din.valid;

   assign din.ready = eotshake;

endmodule
