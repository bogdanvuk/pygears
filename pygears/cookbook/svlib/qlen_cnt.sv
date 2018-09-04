module qlen_cnt #(
                  TDIN = 16,
                  DIN_LVL = 1,
                  CNT_LVL = 1,
                  CNT_ONE_MORE = 0,
                  W_OUT = 16
                  )
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   typedef struct packed {
      logic [DIN_LVL-1:0] eot;
      logic [TDIN-1:0]    data;
   } din_t;

   din_t din_s;
   logic [W_OUT-1:0]      cnt_reg, cnt_next;
   logic                  handshake;
   logic                  part_last;
   logic                  last;

   assign din_s = din.data;
   assign handshake = dout.valid && dout.ready;

   if (CNT_ONE_MORE)
     assign dout.data  = cnt_next;
   else
     assign dout.data  = cnt_reg;

   assign dout.valid = din.valid && last;
   assign din.ready = handshake || !last;

   assign part_last = &din_s.eot[CNT_LVL-1:0];
   assign last = &din_s.eot;
   assign cnt_next = cnt_reg + 1;

   always_ff @(posedge clk) begin
      if (rst | (last && handshake)) begin
         cnt_reg <= '0;
      end else if (din.valid && part_last && !last) begin
         cnt_reg <= cnt_next;
      end
   end

endmodule
