module unary
  #(
    DIN = 16
    )
   (

    input                          clk,
    input                          rst,
    output wire                    din_ready,
    input wire                     din_valid,
    input wire [DIN-1:0]           din_data,

    input wire                     dout_ready,
    output wire                    dout_valid,
    output wire [(2**(DIN-1))-1:0] dout_data
    );

   assign dout_valid = din_valid;
   assign din_ready  = dout_ready;

   genvar                             i;

   generate
      for (i = 0; i < 2**(DIN-1); i++) begin
         assign dout_data[i] = (i < din_data);
      end
   endgenerate

endmodule
