module fixed_latency_decoupler # (
                                  parameter DATA_W = 16,                 // Data Width
                                  parameter LATENCY = 3                  // Number of pipeline Registers
                                  )
   (
    input logic              clk,
    input logic              rst,
    input logic              din_valid,
    input logic [DATA_W-1:0] dout_data,
    output logic             din_ready,
                             dti.producer dout
    );

   logic                     dout_valid_pipe[LATENCY-1:0];                // Pipelines for decouple_mem enable
   logic                     dout_valid_pipe_out;
   integer                   i;

   always @ (posedge clk) begin
      if (rst) begin
         dout_valid_pipe[0] <= 1'b0;
      end else begin
         dout_valid_pipe[0] <= din_valid;
      end

      for (i=0; i<LATENCY-1; i=i+1)
        dout_valid_pipe[i+1] <= dout_valid_pipe[i];
   end

   assign dout_valid_pipe_out = dout_valid_pipe[LATENCY-1];

   // localparam MSB = $clog2(LATENCY + 1);
   localparam MSB = $clog2(LATENCY + 2);

   localparam DECOUPLE_DEPTH = 2**MSB;

   logic [DATA_W-1 : 0] decouple_mem [0 : DECOUPLE_DEPTH-1];
   logic [MSB:0]        w_ptr;
   logic [MSB:0]        r_ptr;
   logic [MSB-1:0]      cnt;
   logic                empty;
   logic                full;


   assign empty = (w_ptr == r_ptr);
   assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);
   assign cnt = signed'(w_ptr) - signed'(r_ptr);

   initial begin
      r_ptr = 0;
      w_ptr = 0;
   end

   always @(posedge clk) begin
      if(rst) begin
         w_ptr <= 0;
      end else if(dout_valid_pipe_out & (!full)) begin
         w_ptr <= w_ptr + 1;
         decouple_mem[w_ptr[MSB-1:0]] <= dout_data;
      end
   end

   always @(posedge clk) begin
      if(rst) begin
         r_ptr <= 0;
      end else if(dout.ready & ~empty) begin
         r_ptr <= r_ptr + 1;
      end
   end

   assign din_ready = (cnt <= 1) && (!full);
   // assign din_ready = empty || dout.ready;
   assign dout.data = decouple_mem[r_ptr[MSB-1:0]];
   assign dout.valid = ~empty;

endmodule
