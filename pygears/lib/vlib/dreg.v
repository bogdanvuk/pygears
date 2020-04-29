module dreg #(
              parameter DIN = 0,
              parameter INIT = 0,
              parameter INIT_VALID = 0
             )
   (
    input                 clk,
    input                 rst,

    output wire           din_ready,
    input wire            din_valid,
    input wire [DIN-1:0]  din_data,

    input wire            dout_ready,
    output wire           dout_valid,
    output wire [DIN-1:0] dout_data
    );

   reg [$size(din_data)-1 : 0] din_reg_data;
   reg                         din_reg_valid;
   wire                         reg_empty;
   wire                         reg_ready;

   assign reg_ready = reg_empty | dout_ready;
   assign reg_empty = !din_reg_valid;

   initial begin
      din_reg_valid = INIT;
   end

   always @(posedge clk)
     begin
        if(rst) begin
           din_reg_valid <= INIT_VALID;
           if (INIT_VALID)
             din_reg_data <= INIT;
        end else if (reg_ready) begin
           din_reg_valid <= din_valid;
           din_reg_data <= din_data;
        end
     end

   assign din_ready = reg_ready;
   assign dout_data = din_reg_data;
   assign dout_valid = din_reg_valid;

endmodule
