module decoupler
   #(
	   parameter DEPTH = 2,
     parameter DIN = 16
	   )
   (
    input                 clk,
    input                 rst,

    output wire           din_ready,
    input wire            din_valid,
    input wire [DIN-1:0]  din_data,

    input wire            dout_ready,
    output wire           dout_valid,
    output wire [DIN-1:0] dout_data
    );

   localparam MSB = $clog2(DEPTH);
   localparam W_DATA = DIN;

   reg [MSB:0]            w_ptr;
   reg [MSB:0]            r_ptr;
   reg [W_DATA-1 : 0] memory [0 : DEPTH-1];
   wire                   empty;
   wire                   full;

   initial begin
      r_ptr = 0;
      w_ptr = 0;
   end

   assign empty = (w_ptr == r_ptr);
   assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);

   always @(posedge clk) begin
      if(rst) begin
         w_ptr <= 0;
      end else if(din_valid & ~full) begin
         w_ptr <= w_ptr + 1;
      end
   end

   always @(posedge clk) begin
      if (~full) begin
         memory[w_ptr[MSB-1:0]] <= din_data;
      end
   end

   always @(posedge clk) begin
      if(rst) begin
         r_ptr <= 0;
      end else if(dout_ready & ~empty) begin
         r_ptr <= r_ptr + 1;
      end
   end

   assign dout_data = memory[r_ptr[MSB-1:0]];
   assign dout_valid = ~empty;

   assign din_ready = ~full;

endmodule
