module buff
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

   assign reg_ready = reg_empty;
   assign reg_empty = !din_reg_valid;

   initial begin
      din_reg_valid = 0;
   end

   always @(posedge clk)
     begin
        if(rst | (!reg_empty && dout.ready)) begin
           din_reg_valid <= '0;
        end else if (reg_ready)begin
           din_reg_valid <= din.valid;
           din_reg_data <= din.data;
        end
     end

   assign din.ready = reg_ready;
   assign dout.data = din_reg_data;
   assign dout.valid = din_reg_valid;

   // ---------------------------------------------------------------------------
   // Usage checks
   // ---------------------------------------------------------------------------

   if ($size(din.data) != $size(dout.data))
     $error("Reg incorrect usage: output data must be same width as input data");

endmodule
