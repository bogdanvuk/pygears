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

   localparam MSB = $clog2(LATENCY + 1);

   localparam DECOUPLE_DEPTH = 2**MSB;

   logic [DATA_W-1 : 0] decouple_mem [0 : DECOUPLE_DEPTH-1];
   logic [MSB:0]        w_ptr;
   logic [MSB:0]        r_ptr;
   logic [MSB:0]        w_ptr_next;
   logic [MSB:0]        r_ptr_next;
   logic [MSB-1:0]      cnt;
   logic [MSB-1:0]      cnt_next;
   logic                almost_empty;
   logic                non_empty;
   logic                full;
   logic                full_next;


   // assign full = (w_ptr[MSB-1:0] == r_ptr[MSB-1:0]) & (w_ptr[MSB]!=r_ptr[MSB]);
   // assign cnt = signed'(w_ptr) - signed'(r_ptr);
   assign cnt_next = signed'(w_ptr_next) - signed'(r_ptr_next);
   assign full_next = (w_ptr_next[MSB-1:0] == r_ptr_next[MSB-1:0]) && (w_ptr_next[MSB]!=r_ptr_next[MSB]);

   always @(posedge clk)
     almost_empty <= (cnt_next <= 1) && (!full_next);
     // assign almost_empty <= (cnt_next <= 1);

   initial begin
      r_ptr = 0;
      w_ptr = 0;
      full = 0;
      non_empty = 0;
      almost_empty = 1;
   end

   always_comb begin
      w_ptr_next = w_ptr;
      if(rst) begin
         w_ptr_next = 0;
      end else if(dout_valid_pipe_out & (!full)) begin
         w_ptr_next = w_ptr + 1;
      end
   end

   always_comb begin
      r_ptr_next = r_ptr;
      if(rst) begin
         r_ptr_next = 0;
      end else if(rd_ready & non_empty) begin
         r_ptr_next = r_ptr + 1;
      end
   end

   always @(posedge clk)
     non_empty <= (w_ptr_next != r_ptr_next);

   always @(posedge clk)
     full <= full_next;

   always @(posedge clk)
     w_ptr <= w_ptr_next;

   always @(posedge clk)
     r_ptr <= r_ptr_next;

   always @(posedge clk) begin
      if(dout_valid_pipe_out & (!full)) begin
         decouple_mem[w_ptr[MSB-1:0]] <= dout_data;
      end
   end

   // assign din_ready = almost_empty && (!full);
   assign din_ready = almost_empty;
   // assign dout.data = decouple_mem[r_ptr[MSB-1:0]];
   // assign dout.valid = non_empty;

   logic [DATA_W-1 : 0] mem_reg;
   logic                reg_non_empty;

   initial begin
      reg_non_empty = 1;
   end

   logic rd_ready;
   assign rd_ready = ~reg_non_empty | dout.ready;

   always @(posedge clk) begin
      if (rst) begin
         reg_non_empty <= 0;
      end else if (rd_ready) begin
         mem_reg <= decouple_mem[r_ptr[MSB-1:0]];
         reg_non_empty <= non_empty;
      end
   end

   assign dout.data = mem_reg;
   assign dout.valid = reg_non_empty;

endmodule
