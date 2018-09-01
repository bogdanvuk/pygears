module decoupler
   #(
	   parameter DEPTH = 2,
     parameter DIN = 16
	   )
   (
    input logic clk,
    input       rst,
    dti.consumer din,
    dti.producer dout
    );

    if (DEPTH > 1) begin

      localparam MSB = $clog2(DEPTH);
      localparam W_DATA = DIN;

      logic [MSB:0] w_ptr;
      logic [MSB:0] r_ptr;
      logic empty;
      logic full;

      logic [W_DATA : 0] memory [0 : DEPTH-1]; //one bit for valid

      assign empty = (w_ptr == r_ptr);
      assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);

      always_ff @(posedge clk) begin
        if(rst) begin
          w_ptr <= 0;
          for (int i = 0; i < DEPTH; i++) begin
            memory[i] <= '0;
          end
        end else if(din.valid & ~full) begin
          w_ptr <= w_ptr + 1;
          memory[w_ptr[MSB-1:0]] <= {din.data, din.valid};
        end
      end

      always_ff @(posedge clk) begin
        if(rst) begin
          r_ptr <= 0;
        end else if(dout.ready & ~empty) begin
          r_ptr <= r_ptr + 1;
        end
      end

      assign dout.data = memory[r_ptr[MSB-1:0]][W_DATA:1];
      assign dout.valid = memory[r_ptr[MSB-1:0]][0] & ~empty;

      assign din.ready = ~full;

   end else begin

      logic [DIN-1 : 0] din_reg_data;
      logic                         din_reg_valid;
      logic                         reg_empty;
      logic                         reg_ready;

      assign reg_ready = reg_empty;
      assign reg_empty = !din_reg_valid;

      always_ff @(posedge clk) begin
         if(rst | (!reg_empty && dout.ready)) begin
            din_reg_valid <= '0;
         end else if (reg_ready)begin
            din_reg_valid <= din.valid;
            din_reg_data <= din.data;
         end
      end

      assign din.ready = reg_ready;
      assign dout.data = din_reg_data;
      assign dout.valid = din_reg_valid;
   end

endmodule : decoupler
