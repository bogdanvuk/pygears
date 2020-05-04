module shred #(
               parameter DIN = 0
               ) (
                  input                clk,
                  input                rst,

                  output wire          din_ready,
                  input wire           din_valid,
                  input wire [DIN-1:0] din_data
                  );
   assign din_ready = 1'b1;
endmodule
