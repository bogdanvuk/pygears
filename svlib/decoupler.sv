module decoupler#(DEPTH = 2)
   (
    input logic clk,
    input       rst,
    dti.consumer din,
    dti.producer dout
    );

    localparam MSB = $clog2(DEPTH);
    localparam W_DATA = $size(din.data);

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

   // ---------------------------------------------------------------------------
   // Usage checks
   // ---------------------------------------------------------------------------

   if ($size(din.data) != $size(dout.data))
     $error("Ready cutter incorrect usage: output data must be same width as input data");

endmodule : decoupler
