module flatten
  #(
    parameter TDIN = 17,
    parameter DIN_LVL = 1,
    parameter DOUT_LVL = 1
    )
   (
    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout
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

   typedef struct  packed {
      logic [TDIN-1:0] data;
   } dout_flat_t;

   if (DOUT_LVL >= 2) begin
      din_queue_t in_data;
      dout_queue_t out_data;

      assign in_data = din.data;
      assign out_data.eot = {in_data.out_eot & in_data.flat_eot};
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

//interface assignments
   assign dout.dvalid = din.dvalid;
   assign dout.eot    = din.eot;
   assign din.dready = dout.dready;

endmodule : flatten
