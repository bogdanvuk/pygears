module accumulator #(
                     parameter W_DATA = 16
              )
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   typedef struct packed
                  {
                     logic eot;
                     logic [W_DATA-1 : 0] offset;
                     logic [W_DATA-1 : 0] data;
                  } din_t;

   din_t din_s;
   logic [W_DATA-1 : 0] acc;
   logic [W_DATA-1 : 0] add_term;
   logic offset_added;
   logic acc_done;
   logic din_handshake;
   logic dout_handshake;

   assign din_s = din.data;
   assign din_handshake = din.valid && din.ready;
   assign dout_handshake = dout.valid && dout.ready;

   always_ff @(posedge clk) begin
     if(rst) begin
        acc <= 0;
     end else if (din_handshake) begin
        acc <= add_term + din_s.data;
     end
   end

   always_ff @(posedge clk) begin
      if(rst | (din_handshake && din_s.eot))begin
         offset_added <= 0;
      end else begin
         offset_added <= din_handshake || offset_added;
      end

   end

   always_ff @(posedge clk) begin
      if(rst || (dout_handshake && !din_handshake)) begin
         acc_done <= 0;
      end else if(din_handshake) begin
         acc_done <= din_s.eot;
      end
   end

   assign add_term = offset_added ? acc : din_s.offset;

   assign dout.valid = acc_done;
   assign din.ready = (dout.ready || !dout.valid);
   assign dout.data = acc;

 endmodule : accumulator
