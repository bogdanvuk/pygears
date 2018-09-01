module qfilt #(
               parameter W_DIN = 16,
               parameter W_DOUT = 16,
               parameter LVL = 1,
               parameter SEL = 0,
               parameter FILT_LVL = 0
              )
  (
   input clk,
   input rst,
   dti.consumer din,
   dti.producer dout
   );

   typedef struct packed
                  {
                     logic [LVL-1:0] eot;
                     logic       ctrl;
                     logic [W_DIN-1:0] data;
                  } din_t;

   typedef struct packed
                  {
                     logic [LVL-1:0] eot;
                     logic [W_DOUT-1:0] data;
                  } dout_t;

   din_t din_s;
   dout_t dout_reg;
   logic valid_reg;
   logic reg_empty;
   logic eot_load;
   logic field_sel;
   logic din_eot;
   logic dout_eot;
   logic eot_merge;

   assign din_s = din.data;
   assign field_sel = (din_s.ctrl == SEL);

   assign din_eot = din_s.eot[0];
   assign dout_eot = &dout_reg.eot[FILT_LVL-1:0];

   assign handshake = dout.valid && dout.ready;
   assign din_sel_valid = din.valid && field_sel;

   assign data_load = din_sel_valid && (reg_empty || handshake);
   assign dout.valid = !reg_empty && (din_sel_valid || dout_eot);

   assign eot_merge = din.valid && din_eot && !field_sel && (!dout.valid || handshake);

   assign reg_empty = !valid_reg;
   assign eot_load = data_load || eot_merge;

   always_ff @(posedge clk) begin
      if (rst || (handshake && !data_load)) begin
         dout_reg <= '0;
         valid_reg <= '0;
      end else begin
         if (eot_load) begin
            dout_reg.eot <= din_s.eot;
         end

         if (data_load) begin
            valid_reg <= '1;
            dout_reg.data <= din_s.data;
         end
      end
   end

   assign dout.data = dout_reg;

   assign din.ready = eot_load || (!field_sel && !din_eot && din.valid);

endmodule
