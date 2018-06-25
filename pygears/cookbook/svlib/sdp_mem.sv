
module sdp_mem #(
                 W_DATA = 16,
                 W_ADDR = 6,
                 DEPTH = 64
                 )
   (
    input                         clk,
    input                         ena, // primary global enable
    input                         enb, // dual global enable
    input                         wea, // primary write enable
    input [W_ADDR-1:0]        addra, // write address / primary read address
    input [W_ADDR-1:0]        addrb, // dual read address
    input [W_DATA-1:0]        dia, // primary data input
    output logic [W_DATA-1:0] dob    //dual output port
    );

   logic [W_DATA-1:0]         ram [DEPTH-1:0];

   always_ff @(posedge clk) begin
      if (ena) begin
         if (wea) begin
            ram[addra] <= dia;
         end
      end
   end

   always @(posedge clk) begin
      if (enb) begin
         dob <= ram[addrb];
      end
   end

endmodule
