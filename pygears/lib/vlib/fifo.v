module fifo
  #(
	  parameter DEPTH = 64,
    parameter THRESHOLD = 0,
    parameter DIN = 16,
    parameter REGOUT = 0
	  )
	 (
	  input logic           clk,
	  input logic           rst,
    output wire           din_ready,
    input wire            din_valid,
    input wire [DIN-1:0]  din_data,

    input wire            dout_ready,
    output wire           dout_valid,
    output wire [DIN-1:0] dout_data
	  ) ;

	 localparam CW = $clog2(DEPTH);
	 localparam WIDTH = DIN;

	 logic [WIDTH-1:0] ram [0:DEPTH-1];
	 logic [CW:0]      raddr_reg;
	 logic [CW:0]      raddr_next;
	 logic [CW:0]      waddr_reg;
	 logic [CW:0]      waddr_next;

   logic [CW:0]      fifo_load_tmp;
   logic [CW-1:0]    fifo_load;
   logic             fifo_valid;
   logic             out_ready;
   logic             out_valid;
   logic             out_handshake;

	 logic             we;
	 wire              dv = waddr_reg != raddr_reg;

   logic [WIDTH-1:0]  out_buff;

	 wire              eq_cnt = waddr_reg[CW-1:0] == raddr_reg[CW-1:0];
	 wire              eq_msb = waddr_reg[CW] == raddr_reg[CW];
	 wire              full = eq_cnt & ~eq_msb;
	 wire              empty = eq_cnt & eq_msb;

	 logic [WIDTH-1:0] in_buff;

   logic             thr_reached;

   assign fifo_load_tmp = waddr_reg - raddr_reg;
   assign fifo_load = fifo_load_tmp[CW-1 : 0];

   assign thr_reached = fifo_load > (THRESHOLD - 1);

   if ( THRESHOLD ) begin
      assign fifo_valid = ~empty && thr_reached;
   end else begin
      assign fifo_valid = ~empty;
   end

   assign in_buff = din_data;
	 assign dout_data = out_buff[WIDTH-1:0];
   assign dout_valid = out_valid;

   assign out_handshake = fifo_valid && out_ready;

   if (REGOUT) begin
      always @(posedge clk)
        begin
            if(rst) begin
              out_valid <= '0;
            end else if (out_ready) begin
              out_valid <= fifo_valid;
            end
        end

      assign out_ready = (!out_valid) | dout_ready;

      always @(posedge clk) begin
         if (out_ready) begin
            out_buff <= ram[raddr_reg[CW-1:0]];
         end
      end

   end else begin

      assign out_buff = ram[raddr_reg[CW-1:0]];
      assign out_valid = fifo_valid;
      assign out_ready = dout_ready;

   end


	 always @(posedge clk)
	   if (we == 1'b1)
		   ram[waddr_reg[CW-1:0]] <= in_buff;


	 always @(posedge clk)
	   if (rst)
		   begin
			    raddr_reg <= '0;
			    waddr_reg <= '0;
		   end
	   else
		   begin
			    raddr_reg <= raddr_next;
			    waddr_reg <= waddr_next;
		   end


	 wire ready = out_ready | ~full;
	 assign din_ready = ready;

	 always_comb // Write logic
	   if (din_valid & ready)
		   begin
			    we = 1'b1;
			    waddr_next = waddr_reg + 1'b1;
		   end
	   else
		   begin
			    we = 1'b0;
			    waddr_next = waddr_reg;
		   end

	 always_comb // Read logic
	   if (out_handshake) begin
			  raddr_next = raddr_reg + 1'b1;
		 end else begin
		   raddr_next = raddr_reg;
     end
endmodule
