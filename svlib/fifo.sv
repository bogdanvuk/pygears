module fifo
  #(
	  parameter WIDTH = 16,
	  parameter DEPTH = 64
	  )
	 (
	  input logic clk,
	  input logic rst,
	  dti.consumer din,
	  dti.producer dout
	  ) ;

	 localparam CW = $clog2(DEPTH);

	 logic [WIDTH-1:0] ram [0:DEPTH-1];
	 logic [CW:0]      raddr_reg;
	 logic [CW:0]      raddr_next;
	 logic [CW:0]      waddr_reg;
	 logic [CW:0]      waddr_next;
	 logic             we;
	 wire              dv = waddr_reg != raddr_reg;

	 wire [WIDTH-1:0]  out_buff = ram[raddr_reg[CW-1:0]];

	 wire              eq_cnt = waddr_reg[CW-1:0] == raddr_reg[CW-1:0];
	 wire              eq_msb = waddr_reg[CW] == raddr_reg[CW];
	 wire              full = eq_cnt & ~eq_msb;
	 wire              empty = eq_cnt & eq_msb;

	 logic [WIDTH-1:0] in_buff;

   assign in_buff = din.data;
   assign dout.valid = ~empty;

	 assign dout.data = out_buff[WIDTH-1:0];
	 //assign dout.eot = 1'b0;

	 always @(posedge clk)
	   if (we == 1'b1)
		   ram[waddr_reg[CW-1:0]] <= in_buff;

	 always_ff @(posedge clk)
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


	 wire ready = dout.ready | ~full;//
	 assign din.ready = ready;

	 always_comb // Write logic
	   if (din.valid & ready)
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
	   if (dout.ready & ~empty)
		   begin
			    raddr_next = raddr_reg + 1'b1;
		   end
	   else
		   raddr_next = raddr_reg;
endmodule
