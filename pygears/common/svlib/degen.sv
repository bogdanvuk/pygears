module degen (
              input clk,
              input rst,
              dti.consumer din,
              dti.producer dout
              );

   assign din.ready = 1'b1;

   assign dout.valid = 1'b1;
   assign dout.data   = din.data;

endmodule
