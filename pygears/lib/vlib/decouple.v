// # TODO: Implement latency == 2

module decouple
   #(
	   parameter DEPTH = 2,
     parameter DIN = 16,
     parameter INIT = 0,
     parameter INIT_VALID = 0
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
      wire empty;
      wire full;

      reg [W_DATA-1 : 0] memory [0 : DEPTH-1];

      initial begin
         if (INIT_VALID) begin
            memory[0] = INIT;
            w_ptr = 1;
         end
      end

      assign empty = (w_ptr == r_ptr);
      assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);

      always @(posedge clk) begin
          if(rst) begin
            if (INIT_VALID)
              w_ptr <= 1;
            else
              w_ptr <= 0;
          end else if(din_valid & ~full) begin
            w_ptr <= w_ptr + 1;
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

   end else begin

      reg [DIN-1 : 0] din_reg_data;
      reg             din_reg_valid;
      wire             reg_empty;
      wire             reg_ready;

      assign reg_ready = reg_empty;
      assign reg_empty = !din_reg_valid;

      initial begin
         din_reg_valid = INIT_VALID;
         if (INIT_VALID)
           din_reg_data = INIT;
      end

      always @(posedge clk) begin
         if (rst) begin
            din_reg_valid <= INIT_VALID;
            if (INIT_VALID)
              din_reg_data <= INIT;
          end else if(!reg_empty && dout_ready) begin
            din_reg_valid <= 0;
          end else if (reg_ready)begin
            din_reg_valid <= din_valid;
            din_reg_data <= din_data;
          end
      end

      assign din_ready = reg_ready;
      assign dout_data = din_reg_data;
      assign dout_valid = din_reg_valid;
   end

endmodule
