module round_half_up #(
                       parameter NBITS = 0,
                       parameter DIN = 16
                       )
   (
    input logic clk,
    input       rst,
    dti.consumer din,
    dti.producer dout
    );

   assign dout.valid = din.valid;
   assign din.ready = dout.ready;

   logic [DIN-1:0] dout_data;

   assign dout_data = din.data[DIN-1:0] + { {(DIN-NBITS){1'b0}}, 1'b1, {(NBITS-1){1'b0}}};
   assign dout.data = {{dout_data[DIN-1:NBITS]}, {(NBITS){1'b0}} };

endmodule
