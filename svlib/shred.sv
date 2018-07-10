module shred (
              input clk,
              input rst,
              dti.consumer din);
   assign din.ready = 1'b1;
endmodule
