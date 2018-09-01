module flatten
  #(
    parameter TDIN = 17,
    parameter DIN_LVL = 1,
    parameter DOUT_LVL = 1
    )
   (
    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   typedef struct packed {
      logic [DOUT_LVL-2:0] out_eot;
      logic [DIN_LVL-DOUT_LVL:0] flat_eot;
      logic [TDIN-1:0] data;
   } din_queue_t;

   typedef struct packed {
      logic [DIN_LVL-1:0] flat_eot;
      logic [TDIN-1:0] data;
   } din_flat_t;


   typedef struct packed {
      logic [DOUT_LVL-1:0] eot;
      logic [TDIN-1:0] data;
   } dout_queue_t;

   typedef struct packed {
      logic [TDIN-1:0] data;
   } dout_flat_t;

   if(TDIN>0) begin
      if (DOUT_LVL >= 2) begin
         din_queue_t in_data;
         dout_queue_t out_data;

         assign in_data = din.data;
         assign out_data.eot = {in_data.out_eot, &in_data.flat_eot};
         assign out_data.data = in_data.data;

         assign dout.data = out_data;
      end else if(DOUT_LVL) begin
         din_flat_t in_data;
         dout_queue_t out_data;

         assign in_data = din.data;
         assign out_data.eot = &in_data.flat_eot;
         assign out_data.data = in_data.data;

         assign dout.data = out_data;
      end else begin
         din_flat_t in_data;
         dout_flat_t out_data;

         assign in_data = din.data;
         assign out_data.data = in_data.data;
         assign dout.data = out_data;
      end
   end else begin
      typedef struct packed {
         logic [DOUT_LVL-2:0] out_eot;
         logic [DIN_LVL-DOUT_LVL:0] flat_eot;
      } din_queue_no_data_t;

      din_queue_no_data_t din_s;
      assign din_s = din.data;

      if(DOUT_LVL == 1)begin
         assign dout.data = &din_s.flat_eot;
      end else begin
         assign dout.data = {din_s.out_eot, &din_s.flat_eot};
      end
   end


//interface assignments
   assign dout.valid = din.valid;
   assign din.ready = dout.ready;

endmodule : flatten
