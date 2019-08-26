module round_to_even #(
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

   logic [DIN-1:0] data;

   assign data = din.data[DIN-1:0] + { {(DIN-NBITS){1'b0}}, din.data[NBITS-1], {(NBITS-1){!din.data[NBITS-1]}}};
   assign dout.data = {{data[DIN-1:NBITS]}, {(NBITS){1'b0}} };

endmodule
