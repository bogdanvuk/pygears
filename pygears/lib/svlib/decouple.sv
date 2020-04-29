module decouple
   #(
	   parameter DEPTH = 2,
     parameter DIN = 16,
     parameter INIT = 0,
     parameter INIT_VALID = 0
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

      logic [W_DATA-1 : 0] memory [0 : DEPTH-1];

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
        end else if(din.valid & ~full) begin
          w_ptr <= w_ptr + 1;
          memory[w_ptr[MSB-1:0]] <= din.data;
        end
      end

      always @(posedge clk) begin
        if(rst) begin
          r_ptr <= 0;
        end else if(dout.ready & ~empty) begin
          r_ptr <= r_ptr + 1;
        end
      end

      assign dout.data = memory[r_ptr[MSB-1:0]];
      assign dout.valid = ~empty;

      assign din.ready = ~full;

   end else begin

      logic [DIN-1 : 0] din_reg_data;
      logic                         din_reg_valid;
      logic                         reg_empty;
      logic                         reg_ready;

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
         end else if(!reg_empty && dout.ready) begin
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

endmodule
