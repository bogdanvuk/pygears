module state
  #(
    parameter INIT = 0
    )
   (
    input logic rst,
    input logic clk,
	  dti.consumer din,
	  dti.consumer rd,
	  dti.producer dout
    );

   logic [$size(din.data)-1 : 0] data_reg = INIT;

   always_ff @(posedge clk) begin
      if (rst) begin
         data_reg <= INIT;
      end else if (din.valid && din.ready) begin
         data_reg <= din.data;
      end
   end

   assign dout.data = data_reg;
   assign dout.valid = rd.valid;

   assign rd.ready = dout.ready;
   // assign din.ready = dout.ready ? rd.valid : 1'b1;
   assign din.ready = 1'b1;

endmodule
