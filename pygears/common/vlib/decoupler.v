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

    if (DEPTH > 1) begin

       localparam MSB = $clog2(DEPTH);
       localparam W_DATA = DIN;

       reg [MSB:0] w_ptr;
       reg [MSB:0] r_ptr;
       reg [W_DATA : 0] memory [0 : DEPTH-1]; //one bit for valid
       wire             empty;
       wire             full;

       initial begin
          r_ptr = 0;
          w_ptr = 0;
       end

      assign empty = (w_ptr == r_ptr);
      assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);

      // Because of Verilator issues:
      //   memory[w_ptr[MSB-1:0]] replaced with for loop
      //   {din_data, din_valid} first assigned to w_data
      integer i;
      wire [W_DATA:0]  w_data = {din_data, din_valid};
      always @(posedge clk) begin
        if(rst) begin
          w_ptr <= 0;
        end else if(din_valid & ~full) begin
          w_ptr <= w_ptr + 1;
         for(i = 0; i < DEPTH; i=i+1)
           if (i == w_ptr[MSB-1:0])
              memory[i] <= w_data;
        end
      end

      always @(posedge clk) begin
        if(rst) begin
          r_ptr <= 0;
        end else if(dout_ready & ~empty) begin
          r_ptr <= r_ptr + 1;
        end
      end

      assign dout_data = memory[r_ptr[MSB-1:0]][W_DATA:1];
      assign dout_valid = memory[r_ptr[MSB-1:0]][0] & ~empty;

      assign din_ready = ~full;

   end
   //  else begin

   //    reg [DIN-1 : 0] din_reg_data;
   //    reg                         din_reg_valid;
   //    wire                         reg_empty;
   //    wire                         reg_ready;

   //    assign reg_ready = reg_empty;
   //    assign reg_empty = !din_reg_valid;

   //    always_ff @(posedge clk) begin
   //       if(rst | (!reg_empty && dout.ready)) begin
   //          din_reg_valid <= '0;
   //       end else if (reg_ready)begin
   //          din_reg_valid <= din.valid;
   //          din_reg_data <= din.data;
   //       end
   //    end

   //    assign din.ready = reg_ready;
   //    assign dout.data = din_reg_data;
   //    assign dout.valid = din_reg_valid;
   // end

endmodule
