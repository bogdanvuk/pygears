module shred (
              input logic clk,
              input logic rst,
              dti.consumer din);
   assign din.ready = 1'b1;
endmodule
