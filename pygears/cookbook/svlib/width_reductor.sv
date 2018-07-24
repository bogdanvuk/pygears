module width_reductor
  #(
    W_DATA = 16,
    NO = 4
    )
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   typedef logic [NO-1:0] [W_DATA-1:0] din_t;

   din_t din_array;
   logic dout_handshake;
   logic [$clog2(NO)-1 : 0] cnt;
   logic [$clog2(NO)-1 : 0] cnt_next;
   logic last;

   assign din_array = din.data;
   assign dout_handshake = dout.valid && dout.ready;

   always_ff @(posedge clk) begin
      if (rst) begin
         cnt <= 0;
      end else if(dout_handshake) begin
         cnt <= cnt_next;
      end
   end

   always_comb begin
      if (cnt < NO-1)
         cnt_next = cnt + 1;
      else
         cnt_next = 0;
   end

   assign last = (cnt == NO-1) && din.valid;

   assign dout.valid = din.valid;
   assign dout.data = {last, din_array[cnt]};
   assign din.ready = last && dout_handshake;

   endmodule : width_reductor
