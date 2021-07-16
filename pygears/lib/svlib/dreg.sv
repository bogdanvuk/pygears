module dreg #(parameter DIN = 16,
              parameter INIT = 0,
              parameter INIT_VALID = 0
              )
   (
    input logic clk,
    input logic rst,
    dti.consumer din,
    dti.producer dout
    );

   logic [$size(din.data)-1 : 0] din_reg_data;
   logic                         din_reg_valid;
   logic                         reg_empty;
   logic                         reg_ready;

   assign reg_ready = reg_empty | dout.ready;
   assign reg_empty = !din_reg_valid;

   initial begin
      din_reg_valid = INIT_VALID;
      if (INIT_VALID)
        din_reg_data = INIT;
   end

   always @(posedge clk)
     begin
        if (rst) begin
           din_reg_valid <= INIT_VALID;
           if (INIT_VALID)
             din_reg_data <= INIT;
        end else if (reg_ready) begin
           din_reg_valid <= din.valid;
           din_reg_data <= din.data;
        end
     end

   assign din.ready = reg_ready;
   assign dout.data = din_reg_data;
   assign dout.valid = din_reg_valid;

endmodule
