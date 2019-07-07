module project
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
      logic [DIN_LVL-DOUT_LVL-1:0] cut_eot;
      logic [DOUT_LVL-1:0] out_eot;
      logic [TDIN-1:0] data;
   } din_queue_t;

   typedef struct packed {
      logic [DOUT_LVL-1:0] eot;
      logic [TDIN-1:0] data;
   } dout_queue_t;

   typedef struct  packed {
      logic [TDIN-1:0] data;
   } dout_flat_t;

   if (DOUT_LVL) begin
      din_queue_t in_data;
      dout_queue_t out_data;

      assign in_data = din.data;
      assign out_data.eot = in_data.out_eot;
      assign out_data.data = in_data.data;

      assign dout.data = out_data;
   end else begin
      din_queue_t in_data;
      dout_flat_t out_data;

      assign in_data = din.data;
      assign out_data.data = in_data.data;
      assign dout.data = out_data;
   end

//interface assignments
   assign dout.valid = din.valid;
   //assign dout.eot    = din.eot;
   assign din.ready = dout.ready;

endmodule
